"""Answer orchestration: retrieval, streaming, citation validation, persistence.

The route layer only checks ownership and starts the exchange. Everything below
runs in a generator with its own database session, because a streaming response
outlives the request-scoped session supplied by FastAPI dependencies.
"""

import json
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

from app.ai.embeddings import get_embedder
from app.ai.llm import GroqLLM
from app.ai.pipeline import AnswerFieldExtractor, AnswerPipeline, build_grounded_answer
from app.ai.types import GroundedAnswer, RetrievedChunk
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.conversation import Citation, Conversation, Message
from app.models.document import Document
from app.repositories import conversations as conversation_repo
from app.repositories import documents as document_repo

logger = get_logger("insurio.answering")


def sse(event: str, payload: dict) -> str:
    """Serialise one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


def build_pipeline(settings: Settings, top_k: int | None = None) -> AnswerPipeline:
    return AnswerPipeline(
        llm=GroqLLM(settings),
        embedder=get_embedder(settings),
        top_k=top_k or settings.RETRIEVAL_TOP_K,
        candidates=settings.RETRIEVAL_CANDIDATES,
        min_score=settings.RETRIEVAL_MIN_SCORE,
    )


def _source_list(sources: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "source_id": f"S{index}",
            "page_start": source.page_start,
            "page_end": source.page_end,
            "heading": source.heading,
        }
        for index, source in enumerate(sources, start=1)
    ]


def _history(db, conversation_id: uuid.UUID, exclude_id: uuid.UUID) -> list[dict[str, str]]:
    rows = conversation_repo.recent_messages(db, conversation_id, limit=8)
    return [
        {"role": row.role, "content": row.content}
        for row in rows
        if row.id != exclude_id and row.content.strip()
    ][-6:]


def _persist_answer(
    db,
    *,
    assistant: Message,
    document_id: uuid.UUID,
    answer: GroundedAnswer,
    model_name: str,
    retrieval_mode: str,
    latency_ms: int,
) -> dict:
    assistant.content = answer.answer_markdown
    assistant.status = "complete"
    assistant.model = model_name
    assistant.retrieval_mode = retrieval_mode
    assistant.latency_ms = latency_ms
    assistant.confidence = answer.confidence
    assistant.insufficient_evidence = answer.insufficient_evidence
    assistant.citation_status = answer.citation_status
    assistant.error_message = None
    assistant.metadata_json = {
        "stated": answer.stated,
        "inferred": answer.inferred,
        "not_in_document": answer.not_in_document,
        "invalid_citations": answer.invalid_citations,
    }
    db.add(assistant)

    for existing in list(assistant.citations):
        db.delete(existing)
    citations: list[Citation] = []
    for citation in answer.citations:
        chunk_id = citation.chunk_id if isinstance(citation.chunk_id, uuid.UUID) else None
        record = Citation(
            message_id=assistant.id,
            document_id=document_id,
            chunk_id=chunk_id,
            source_id=citation.source_id,
            page_start=citation.page_start,
            page_end=citation.page_end,
            quote=citation.quote,
            is_valid=citation.is_valid,
        )
        db.add(record)
        citations.append(record)
    db.commit()

    return {
        "id": str(assistant.id),
        "role": "assistant",
        "content": answer.answer_markdown,
        "status": "complete",
        "citations": [
            {
                "source_id": citation.source_id,
                "page_start": citation.page_start,
                "page_end": citation.page_end,
                "quote": citation.quote,
                "is_valid": citation.is_valid,
            }
            for citation in citations
        ],
        "confidence": answer.confidence,
        "insufficient_evidence": answer.insufficient_evidence,
        "citation_status": answer.citation_status,
        "model": model_name,
        "latency_ms": latency_ms,
        "stated": answer.stated,
        "inferred": answer.inferred,
        "not_in_document": answer.not_in_document,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _fail(assistant_id: uuid.UUID, message: str) -> None:
    with SessionLocal() as db:
        assistant = db.get(Message, assistant_id)
        if assistant is None:
            return
        assistant.status = "failed"
        assistant.content = ""
        assistant.error_message = message[:1000]
        db.add(assistant)
        db.commit()


def stream_exchange(
    *,
    conversation_id: uuid.UUID,
    user_message_id: uuid.UUID,
    assistant_id: uuid.UUID,
    question: str,
    top_k: int | None = None,
) -> Iterator[str]:
    """Yield SSE frames for one question and persist the final answer."""
    settings = get_settings()
    pipeline = build_pipeline(settings, top_k)
    started = time.perf_counter()
    db = SessionLocal()
    conversation: Conversation | None = None
    document_id: uuid.UUID | None = None
    try:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            yield sse("error", {"code": "not_found", "message": "Conversation not found."})
            return
        document_id = conversation.document_id
        document = db.get(Document, document_id)
        if document is None:
            raise AppError("Document not found.", code="document_not_found", status_code=404)
        if document.status != "ready":
            raise AppError(
                "The document has not finished processing.",
                code="document_not_ready",
                status_code=409,
            )

        chunks = document_repo.list_chunks(db, document_id)
        prepared = pipeline.prepare(chunks, question)
        yield sse(
            "meta",
            {
                "conversation_id": str(conversation_id),
                "user_message_id": str(user_message_id),
                "assistant_id": str(assistant_id),
                "retrieval_mode": prepared.retrieval_mode,
                "sources": _source_list(prepared.sources),
                "model": settings.GROQ_MODEL,
            },
        )

        if not prepared.sources:
            answer = pipeline.no_evidence_answer()
        else:
            messages, included = pipeline.messages(
                question, prepared.sources, _history(db, conversation_id, user_message_id)
            )
            extractor = AnswerFieldExtractor()
            raw_parts: list[str] = []
            for delta in pipeline.stream(messages):
                raw_parts.append(delta)
                text = extractor.feed(delta)
                if text:
                    yield sse("delta", {"text": text})
            raw = "".join(raw_parts)
            answer = build_grounded_answer(raw, included)
            if not extractor.emitted_any and answer.answer_markdown:
                yield sse("delta", {"text": answer.answer_markdown})

        latency_ms = int((time.perf_counter() - started) * 1000)
        assistant = db.get(Message, assistant_id)
        if assistant is None:
            yield sse("error", {"code": "not_found", "message": "Answer message not found."})
            return
        payload = _persist_answer(
            db,
            assistant=assistant,
            document_id=document_id,
            answer=answer,
            model_name=pipeline.llm.model_name,
            retrieval_mode=prepared.retrieval_mode,
            latency_ms=latency_ms,
        )
        if conversation is not None:
            conversation_repo.touch(db, conversation)
            db.commit()
        yield sse("final", {"message": payload})
        logger.info(
            "answer_completed",
            extra={"event": "answer_completed", "duration_ms": latency_ms},
        )
    except AppError as exc:
        db.rollback()
        _fail(assistant_id, exc.message)
        yield sse("error", {"code": exc.code, "message": exc.message})
    except Exception:
        db.rollback()
        logger.exception("answer_failed", extra={"event": "answer_failed"})
        _fail(assistant_id, "The answer could not be generated. Please try again.")
        yield sse(
            "error",
            {
                "code": "internal_error",
                "message": "The answer could not be generated. Please try again.",
            },
        )
    finally:
        db.close()


SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
