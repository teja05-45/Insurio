"""Document upload, ingestion, retrieval, and deletion."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.ai.chunking import chunk_pages
from app.ai.embeddings import get_embedder
from app.ai.extraction import build_insight_payload
from app.ai.llm import GroqLLM
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentPage, ProcessingJob
from app.models.user import User
from app.repositories import documents as document_repo
from app.repositories import policies as policy_repo
from app.services import storage
from app.services.pdf import extract_pdf, validate_pdf_bytes

logger = get_logger("insurio.documents")


def create_document(
    db: Session, user: User, *, filename: str, content_type: str, data: bytes
) -> Document:
    settings = get_settings()
    validate_pdf_bytes(data, settings)
    if content_type and content_type not in ("application/pdf", "application/octet-stream"):
        raise AppError("Only PDF uploads are accepted.", code="invalid_file_type", status_code=415)

    display_name = storage.sanitize_filename(filename)
    if not display_name.lower().endswith(".pdf"):
        raise AppError("Only PDF uploads are accepted.", code="invalid_file_type", status_code=415)

    import hashlib

    digest = hashlib.sha256(data).hexdigest()
    existing = db.query(Document).filter_by(user_id=user.id, sha256=digest).first()
    if existing is not None:
        raise AppError(
            "You have already uploaded this document.",
            code="duplicate_document",
            status_code=409,
            details={"document_id": str(existing.id), "status": existing.status},
        )

    storage_key, digest = storage.save_pdf(user.id, data)
    try:
        document = document_repo.create(
            db,
            user_id=user.id,
            original_filename=display_name,
            storage_key=storage_key,
            size_bytes=len(data),
            sha256=digest,
        )
        document_repo.create_job(db, document.id)
        db.commit()
    except Exception:
        storage.delete_pdf(storage_key)
        db.rollback()
        raise
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> None:
    storage_key = document.storage_key
    db.delete(document)
    db.commit()
    storage.delete_pdf(storage_key)


def list_documents(
    db: Session, user_id: uuid.UUID, *, page: int, page_size: int, status: str | None
) -> tuple[list[Document], int]:
    return document_repo.list_for_user(db, user_id, page=page, page_size=page_size, status=status)


def _mark_failed(document_id: uuid.UUID, message: str) -> None:
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            return
        document_repo.mark_failed(db, document, message)
        job = document_repo.latest_job(db, document_id)
        if job is not None:
            job.status = "failed"
            job.error_message = message[:1000]
            job.finished_at = datetime.now(UTC)
            db.add(job)
        db.commit()


def process_document(document_id: uuid.UUID) -> None:
    """Background ingestion. Opens its own session; safe to retry."""
    settings = get_settings()
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return
        job = document_repo.latest_job(db, document_id)
        document.status = "processing"
        document.error_message = None
        if job is not None:
            job.status = "processing"
            job.started_at = datetime.now(UTC)
            job.progress = 10
            job.detail = "Extracting text"
            db.add(job)
        db.commit()

        data = storage.read_pdf(document.storage_key)
        extraction = extract_pdf(data, settings)
        if extraction.encrypted:
            raise AppError(
                "This PDF is password protected. Upload an unlocked copy.",
                code="pdf_encrypted",
            )
        pages_with_text = [p for p in extraction.pages if len(p.text.strip()) >= 20]
        if not pages_with_text:
            raise AppError(
                "No readable text was found. Scanned PDFs require OCR (OCR_ENABLED=true).",
                code="no_extractable_text",
            )

        # Reset previous output so a retry is idempotent.
        db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        db.add_all(
            [
                DocumentPage(
                    document_id=document_id,
                    page_number=page.page_number,
                    text=page.text,
                    char_count=len(page.text),
                    extraction_method=page.extraction_method,
                )
                for page in extraction.pages
            ]
        )
        if job is not None:
            job.progress = 40
            job.detail = "Chunking document"
            db.add(job)
        db.flush()

        drafts = chunk_pages(extraction.pages)
        if not drafts:
            raise AppError("The document produced no usable chunks.", code="no_chunks")

        embedder = get_embedder(settings)
        vectors: list[list[float]] | None = None
        embedding_mode = "disabled"
        if embedder is not None:
            try:
                vectors = embedder.embed_documents([draft.content for draft in drafts])
                embedding_mode = embedder.name
            except Exception:
                logger.warning("embedding_failed", extra={"event": "embedding_failed"})
                vectors = None

        db.add_all(
            [
                DocumentChunk(
                    document_id=document_id,
                    ordinal=draft.ordinal,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    heading=draft.heading,
                    content=draft.content,
                    char_count=len(draft.content),
                    embedding=vectors[index] if vectors else None,
                    embedding_model=embedding_mode if vectors else None,
                )
                for index, draft in enumerate(drafts)
            ]
        )
        if job is not None:
            job.progress = 70
            job.detail = "Extracting policy insights"
            job.metadata_json = {"embedding_mode": embedding_mode}
            db.add(job)
        db.flush()

        llm = (
            GroqLLM(settings)
            if settings.llm_configured and settings.INSIGHTS_LLM_ENRICHMENT
            else None
        )
        payload, method, model = build_insight_payload(
            extraction.pages,
            llm=llm,
            use_llm=llm is not None,
            model_name=settings.GROQ_MODEL,
        )
        policy_repo.upsert_insight(
            db,
            document_id=document_id,
            payload=payload,
            method=method,
            llm_model=model,
        )

        document_repo.mark_ready(
            db, document, page_count=extraction.page_count, chunk_count=len(drafts)
        )
        if job is not None:
            job.status = "ready"
            job.progress = 100
            job.detail = "Ready"
            job.finished_at = datetime.now(UTC)
            job.error_message = None
            db.add(job)
        db.commit()
        logger.info(
            "document_processed",
            extra={"event": "document_processed", "user_id": str(document.user_id)},
        )
    except AppError as exc:
        db.rollback()
        _mark_failed(document_id, exc.message)
        logger.warning("document_processing_failed", extra={"event": "ingest_failed"})
    except Exception:
        db.rollback()
        _mark_failed(document_id, "Processing failed due to an unexpected error.")
        logger.exception("document_processing_error", extra={"event": "ingest_error"})
    finally:
        db.close()


def get_status(db: Session, document: Document) -> tuple[Document, ProcessingJob | None]:
    return document, document_repo.latest_job(db, document.id)


def get_pages(db: Session, document: Document) -> list[DocumentPage]:
    return document_repo.list_pages(db, document.id)


def get_chunks(db: Session, document: Document) -> list[DocumentChunk]:
    return document_repo.list_chunks(db, document.id)
