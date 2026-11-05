"""Document upload, library, workspace, and insight routes."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession, OwnedDocument
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import rate_limit
from app.repositories import documents as document_repo
from app.repositories import policies as policy_repo
from app.schemas.common import MessageResponse, Page
from app.schemas.documents import (
    DocumentDetail,
    DocumentOut,
    DocumentStatusOut,
    InsightFieldOut,
    InsightOut,
    JobOut,
    PageOut,
)
from app.services import documents as document_service
from app.services import insights as insight_service
from app.services import storage

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()
upload_limiter = rate_limit("upload", settings.UPLOAD_RATE_LIMIT_PER_HOUR, 3600)


@router.post(
    "",
    response_model=DocumentDetail,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(upload_limiter)],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="Insurance policy PDF")],
) -> DocumentDetail:
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(
            f"The file exceeds the {settings.MAX_UPLOAD_MB} MB limit.",
            code="file_too_large",
            status_code=413,
        )
    document = document_service.create_document(
        db,
        user,
        filename=file.filename or "policy.pdf",
        content_type=file.content_type or "",
        data=data,
    )
    background_tasks.add_task(document_service.process_document, document.id)
    job = document_repo.latest_job(db, document.id)
    return DocumentDetail(
        **DocumentOut.from_model(document).model_dump(),
        latest_job=JobOut.model_validate(job) if job else None,
    )


@router.get("", response_model=Page[DocumentOut])
def list_documents(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    document_status: str | None = Query(default=None, alias="status"),
) -> Page[DocumentOut]:
    items, total = document_service.list_documents(
        db, user.id, page=page, page_size=page_size, status=document_status
    )
    with_insights = policy_repo.document_ids_with_insights(db, [document.id for document in items])
    return Page(
        items=[
            DocumentOut.from_model(document, has_insights=document.id in with_insights)
            for document in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document: OwnedDocument, db: DbSession) -> DocumentDetail:
    _, job = document_service.get_status(db, document)
    has_insights = policy_repo.get_insight(db, document.id) is not None
    return DocumentDetail(
        **DocumentOut.from_model(document, has_insights=has_insights).model_dump(),
        latest_job=JobOut.model_validate(job) if job else None,
    )


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status(document: OwnedDocument, db: DbSession) -> DocumentStatusOut:
    _, job = document_service.get_status(db, document)
    return DocumentStatusOut(
        id=document.id,
        status=document.status,
        error_message=document.error_message,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        job=JobOut.model_validate(job) if job else None,
    )


@router.get("/{document_id}/pages", response_model=list[PageOut])
def list_pages(document: OwnedDocument, db: DbSession) -> list[PageOut]:
    return [PageOut.model_validate(page) for page in document_service.get_pages(db, document)]


@router.get("/{document_id}/pages/{page_number}", response_model=PageOut)
def get_page(document: OwnedDocument, page_number: int, db: DbSession) -> PageOut:
    page = document_repo.get_page(db, document.id, page_number)
    if page is None:
        raise AppError("Page not found.", code="page_not_found", status_code=404)
    return PageOut.model_validate(page)


@router.get("/{document_id}/file", response_class=FileResponse)
def download_file(document: OwnedDocument) -> FileResponse:
    path = storage.pdf_path(document.storage_key)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            # The middleware default denies framing; this route is the only one
            # that may be embedded, and only by the same origin.
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'self'",
        },
    )


@router.get("/{document_id}/insights", response_model=InsightOut)
def get_insights(document: OwnedDocument, db: DbSession) -> InsightOut:
    insight = insight_service.get_or_extract(db, document, refresh=False)
    return InsightOut(
        document_id=document.id,
        filename=document.original_filename,
        fields=[InsightFieldOut(**field) for field in insight.payload.get("fields", [])],
        meta=insight.payload.get("meta", {}),
        extraction_method=insight.extraction_method,
        llm_model=insight.llm_model,
        updated_at=insight.updated_at,
    )


@router.post("/{document_id}/insights/refresh", response_model=InsightOut)
def refresh_insights(document: OwnedDocument, db: DbSession) -> InsightOut:
    insight = insight_service.get_or_extract(db, document, refresh=True)
    return InsightOut(
        document_id=document.id,
        filename=document.original_filename,
        fields=[InsightFieldOut(**field) for field in insight.payload.get("fields", [])],
        meta=insight.payload.get("meta", {}),
        extraction_method=insight.extraction_method,
        llm_model=insight.llm_model,
        updated_at=insight.updated_at,
    )


@router.delete("/{document_id}", response_model=MessageResponse)
def delete_document(document: OwnedDocument, db: DbSession) -> MessageResponse:
    document_service.delete_document(db, document)
    return MessageResponse(message="Document deleted.")
