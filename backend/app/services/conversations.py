"""Conversation CRUD and answer-message lifecycle."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.repositories import conversations as conversation_repo
from app.repositories import documents as document_repo
from app.schemas.chat import ConversationDetail, ConversationOut, MessageOut


def _document_for(db: Session, conversation: Conversation, user_id: uuid.UUID) -> Document:
    document = document_repo.get_owned(db, conversation.document_id, user_id)
    if document is None:
        raise AppError("Document not found.", code="document_not_found", status_code=404)
    return document


def create(db: Session, user: User, document_id: uuid.UUID, title: str | None) -> ConversationOut:
    document = document_repo.get_owned(db, document_id, user.id)
    if document is None:
        raise AppError("Document not found.", code="document_not_found", status_code=404)
    if document.status != "ready":
        raise AppError(
            "Wait for the document to finish processing before starting a conversation.",
            code="document_not_ready",
            status_code=409,
        )
    conversation = conversation_repo.create(
        db,
        user_id=user.id,
        document_id=document.id,
        title=title or "New conversation",
    )
    db.commit()
    db.refresh(conversation)
    return ConversationOut(
        id=conversation.id,
        document_id=document.id,
        document_filename=document.original_filename,
        title=conversation.title,
        last_activity_at=conversation.last_activity_at,
        created_at=conversation.created_at,
        message_count=0,
        preview=None,
    )


def list_for_user(
    db: Session, user: User, *, page: int, page_size: int
) -> tuple[list[ConversationOut], int]:
    conversations, total = conversation_repo.list_for_user(
        db, user.id, page=page, page_size=page_size
    )
    document_ids = {conversation.document_id for conversation in conversations}
    documents = (
        {
            document.id: document
            for document in db.scalars(select(Document).where(Document.id.in_(document_ids)))
        }
        if document_ids
        else {}
    )
    stats = conversation_repo.stats_for(db, [c.id for c in conversations])
    outputs = []
    for conversation in conversations:
        document = documents.get(conversation.document_id)
        message_count, preview = stats.get(conversation.id, (0, None))
        outputs.append(
            ConversationOut(
                id=conversation.id,
                document_id=conversation.document_id,
                document_filename=document.original_filename if document else None,
                title=conversation.title,
                last_activity_at=conversation.last_activity_at,
                created_at=conversation.created_at,
                message_count=message_count,
                preview=preview,
            )
        )
    return outputs, total


STALE_STREAM_MINUTES = 5


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _heal_interrupted_answers(db: Session, messages: list[Message]) -> bool:
    """A dropped connection leaves a placeholder mid-stream; settle it on read."""
    cutoff = datetime.now(UTC) - timedelta(minutes=STALE_STREAM_MINUTES)
    healed = False
    for message in messages:
        if message.status != "streaming":
            continue
        if _as_utc(message.created_at) >= cutoff:
            continue
        message.status = "failed"
        message.error_message = (
            message.error_message or "The answer was interrupted before it finished."
        )
        db.add(message)
        healed = True
    if healed:
        db.commit()
    return healed


def get_detail(db: Session, conversation: Conversation, user: User) -> ConversationDetail:
    document = _document_for(db, conversation, user.id)
    messages = conversation_repo.list_messages(db, conversation.id)
    _heal_interrupted_answers(db, messages)
    return ConversationDetail(
        id=conversation.id,
        document_id=document.id,
        document_filename=document.original_filename,
        title=conversation.title,
        last_activity_at=conversation.last_activity_at,
        created_at=conversation.created_at,
        message_count=len(messages),
        preview=(messages[-1].content[:160] if messages else None),
        messages=[MessageOut.from_model(message) for message in messages],
    )


def rename(db: Session, conversation: Conversation, title: str) -> None:
    conversation_repo.rename(db, conversation, title)
    db.commit()


def delete(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.commit()


def begin_exchange(
    db: Session, conversation_id: uuid.UUID, question: str
) -> tuple[Message, Message, Conversation]:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise AppError("Conversation not found.", code="not_found", status_code=404)
    if conversation.title in ("New conversation", "", None):
        conversation_repo.rename(db, conversation, question[:80])
    conversation_repo.touch(db, conversation)
    user_message = conversation_repo.add_message(
        db, conversation_id=conversation.id, role="user", content=question
    )
    assistant = conversation_repo.add_message(
        db,
        conversation_id=conversation.id,
        role="assistant",
        content="",
        status="streaming",
    )
    db.commit()
    return user_message, assistant, conversation


def prepare_regenerate(db: Session, conversation: Conversation) -> tuple[str, Message]:
    last_assistant = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    if last_assistant is None:
        raise AppError(
            "There is no answer to regenerate.", code="nothing_to_regenerate", status_code=400
        )
    previous_question = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.role == "user",
            Message.created_at <= last_assistant.created_at,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    if previous_question is None:
        raise AppError(
            "There is no question to regenerate.", code="nothing_to_regenerate", status_code=400
        )

    for citation in list(last_assistant.citations):
        db.delete(citation)
    last_assistant.content = ""
    last_assistant.status = "streaming"
    last_assistant.citations = []
    last_assistant.confidence = None
    last_assistant.insufficient_evidence = False
    last_assistant.citation_status = None
    last_assistant.error_message = None
    db.add(last_assistant)
    db.commit()
    return previous_question.content, last_assistant


def save_failure(assistant_id: uuid.UUID, message: str) -> None:
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        assistant = db.get(Message, assistant_id)
        if assistant is None:
            return
        assistant.status = "failed"
        assistant.content = ""
        assistant.error_message = message[:1000]
        db.add(assistant)
        db.commit()


def add_feedback(
    db: Session, message: Message, user: User, rating: str, comment: str | None
) -> None:
    if message.role != "assistant":
        raise AppError(
            "Feedback applies to assistant answers only.", code="invalid_feedback", status_code=400
        )
    conversation_repo.upsert_feedback(
        db, message_id=message.id, user_id=user.id, rating=rating, comment=comment
    )
    db.commit()


def touch(db: Session, conversation: Conversation) -> None:
    conversation.last_activity_at = datetime.now(UTC)
    db.add(conversation)
