"""Persistence access for documents, pages, chunks, and jobs."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, DocumentPage, ProcessingJob


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    original_filename: str,
    storage_key: str,
    size_bytes: int,
    sha256: str,
) -> Document:
    document = Document(
        user_id=user_id,
        original_filename=original_filename,
        storage_key=storage_key,
        size_bytes=size_bytes,
        sha256=sha256,
        status="queued",
    )
    db.add(document)
    db.flush()
    return document


def get_owned(db: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )


def list_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
) -> tuple[list[Document], int]:
    filters = [Document.user_id == user_id]
    if status:
        filters.append(Document.status == status)
    total = db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def list_ready_for_user(db: Session, user_id: uuid.UUID) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.user_id == user_id, Document.status == "ready")
            .order_by(Document.created_at.desc())
        )
    )


def delete_document(db: Session, document: Document) -> None:
    db.delete(document)


def add_pages(db: Session, document_id: uuid.UUID, pages: list[DocumentPage]) -> None:
    for page in pages:
        page.document_id = document_id
    db.add_all(pages)


def add_chunks(db: Session, chunks: list[DocumentChunk]) -> None:
    db.add_all(chunks)


def replace_chunks(db: Session, document_id: uuid.UUID, chunks: list[DocumentChunk]) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.add_all(chunks)


def list_pages(db: Session, document_id: uuid.UUID) -> list[DocumentPage]:
    return list(
        db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
    )


def get_page(db: Session, document_id: uuid.UUID, page_number: int) -> DocumentPage | None:
    return db.scalar(
        select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
    )


def list_chunks(db: Session, document_id: uuid.UUID) -> list[DocumentChunk]:
    return list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.ordinal)
        )
    )


def mark_ready(db: Session, document: Document, *, page_count: int, chunk_count: int) -> None:
    document.status = "ready"
    document.page_count = page_count
    document.chunk_count = chunk_count
    document.error_message = None
    document.processed_at = datetime.now(UTC)
    db.add(document)


def mark_failed(db: Session, document: Document, message: str) -> None:
    document.status = "failed"
    document.error_message = message[:1000]
    document.processed_at = datetime.now(UTC)
    db.add(document)


def create_job(db: Session, document_id: uuid.UUID) -> ProcessingJob:
    job = ProcessingJob(document_id=document_id, kind="ingest", status="queued", progress=0)
    db.add(job)
    db.flush()
    return job


def latest_job(db: Session, document_id: uuid.UUID) -> ProcessingJob | None:
    return db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at.desc())
    )


def count_for_user(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user_id))
        or 0
    )
