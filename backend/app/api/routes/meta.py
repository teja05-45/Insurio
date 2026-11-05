"""Deployment capability metadata and per-user usage statistics."""

from fastapi import APIRouter

from app.ai.embeddings import embedding_mode
from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.repositories import conversations as conversation_repo
from app.repositories import documents as document_repo
from app.repositories import policies as policy_repo
from app.schemas.chat import UsageSummary
from app.schemas.common import MetaResponse

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        app_version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        llm_configured=settings.llm_configured,
        llm_model=settings.GROQ_MODEL,
        embeddings_mode=embedding_mode(settings),
        ocr_enabled=settings.OCR_ENABLED,
        max_upload_mb=settings.MAX_UPLOAD_MB,
        max_pdf_pages=settings.MAX_PDF_PAGES,
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
    )


@router.get("/usage", response_model=UsageSummary)
def usage(user: CurrentUser, db: DbSession) -> UsageSummary:
    settings = get_settings()
    documents = document_repo.count_for_user(db, user.id)
    conversations = conversation_repo.count_for_user(db, user.id)
    questions = conversation_repo.count_messages_for_user(db, user.id, role="user")
    comparisons = policy_repo.count_for_user(db, user.id)
    quota = settings.PLAN_QUESTION_QUOTA
    percent = round(min(100.0, questions / quota * 100), 1) if quota else 0.0
    return UsageSummary(
        documents=documents,
        conversations=conversations,
        questions=questions,
        comparisons=comparisons,
        quota=quota,
        quota_used_percent=percent,
    )
