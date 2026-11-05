"""Policy insight retrieval and (re)extraction."""

from sqlalchemy.orm import Session

from app.ai.extraction import build_insight_payload
from app.ai.llm import GroqLLM
from app.ai.types import PageText
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.document import Document
from app.models.policy import PolicyInsight
from app.repositories import documents as document_repo
from app.repositories import policies as policy_repo


def _page_texts(db: Session, document: Document) -> list[PageText]:
    return [
        PageText(
            page_number=page.page_number, text=page.text, extraction_method=page.extraction_method
        )
        for page in document_repo.list_pages(db, document.id)
    ]


def get_or_extract(
    db: Session, document: Document, *, refresh: bool = False, allow_llm: bool = True
) -> PolicyInsight:
    if document.status != "ready":
        raise AppError(
            "Insights are available once document processing completes.",
            code="document_not_ready",
            status_code=409,
            details={"status": document.status},
        )
    existing = policy_repo.get_insight(db, document.id)
    if existing is not None and not refresh:
        return existing

    pages = _page_texts(db, document)
    if not pages:
        raise AppError("The document has no extracted pages.", code="no_pages", status_code=409)

    settings = get_settings()
    use_llm = allow_llm and settings.llm_configured and settings.INSIGHTS_LLM_ENRICHMENT
    payload, method, model = build_insight_payload(
        pages,
        llm=GroqLLM(settings) if use_llm else None,
        use_llm=use_llm,
        model_name=settings.GROQ_MODEL,
    )
    insight = policy_repo.upsert_insight(
        db,
        document_id=document.id,
        payload=payload,
        method=method,
        llm_model=model,
    )
    db.commit()
    db.refresh(insight)
    return insight
