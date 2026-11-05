"""Persistence access for conversations, messages, citations, and feedback."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Citation, Conversation, Feedback, Message


def create(db: Session, *, user_id: uuid.UUID, document_id: uuid.UUID, title: str) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        document_id=document_id,
        title=title[:200],
        last_activity_at=datetime.now(UTC),
    )
    db.add(conversation)
    db.flush()
    return conversation


def get_owned(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )


def list_for_user(
    db: Session, user_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Conversation], int]:
    total = (
        db.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
        or 0
    )
    items = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.last_activity_at.desc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def list_with_stats(
    db: Session, user_id: uuid.UUID, limit: int = 20
) -> list[tuple[Conversation, int, str | None]]:
    """Return conversation, message count, and last message preview in two queries."""
    conversations = list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.last_activity_at.desc().nullslast())
            .limit(limit)
        )
    )
    if not conversations:
        return []

    ids = [c.id for c in conversations]
    counts = dict(
        db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(Message.conversation_id.in_(ids))
            .group_by(Message.conversation_id)
        ).all()
    )
    last_rows = db.execute(
        select(Message.conversation_id, Message.content)
        .where(Message.conversation_id.in_(ids))
        .order_by(Message.conversation_id, Message.created_at.desc())
    ).all()
    previews: dict[uuid.UUID, str] = {}
    for conversation_id, content in last_rows:
        previews.setdefault(conversation_id, content[:160])
    return [(c, counts.get(c.id, 0), previews.get(c.id)) for c in conversations]


def stats_for(
    db: Session, conversation_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, str | None]]:
    """Message counts and last-message previews for a page of conversations."""
    if not conversation_ids:
        return {}
    counts = dict(
        db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
        ).all()
    )
    ranked = (
        select(
            Message.conversation_id.label("conversation_id"),
            Message.content.label("content"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=Message.created_at.desc(),
            )
            .label("row_number"),
        )
        .where(Message.conversation_id.in_(conversation_ids))
        .subquery()
    )
    previews = dict(
        db.execute(
            select(ranked.c.conversation_id, ranked.c.content).where(ranked.c.row_number == 1)
        ).all()
    )
    return {
        conversation_id: (
            counts.get(conversation_id, 0),
            (previews.get(conversation_id) or "")[:160] or None,
        )
        for conversation_id in conversation_ids
    }


def count_for_user(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
        or 0
    )


def last_user_message_id(db: Session, conversation_id: uuid.UUID) -> uuid.UUID | None:
    return db.scalar(
        select(Message.id)
        .where(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(1)
    )


def delete_conversation(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)


def touch(db: Session, conversation: Conversation) -> None:
    conversation.last_activity_at = datetime.now(UTC)
    db.add(conversation)


def rename(db: Session, conversation: Conversation, title: str) -> None:
    conversation.title = title[:200]
    db.add(conversation)


def add_message(
    db: Session,
    *,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    status: str = "complete",
    model: str | None = None,
    retrieval_mode: str | None = None,
    latency_ms: int | None = None,
    confidence: float | None = None,
    insufficient_evidence: bool = False,
    citation_status: str | None = None,
    metadata_json: dict | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        status=status,
        model=model,
        retrieval_mode=retrieval_mode,
        latency_ms=latency_ms,
        confidence=confidence,
        insufficient_evidence=insufficient_evidence,
        citation_status=citation_status,
        metadata_json=metadata_json,
    )
    db.add(message)
    db.flush()
    return message


def get_message(db: Session, message_id: uuid.UUID) -> Message | None:
    return db.get(Message, message_id)


def list_messages(db: Session, conversation_id: uuid.UUID) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.citations))
            .order_by(Message.created_at)
        )
    )


def recent_messages(db: Session, conversation_id: uuid.UUID, limit: int = 8) -> list[Message]:
    rows = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.status == "complete")
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
    )
    return list(reversed(rows))


def count_messages_for_user(db: Session, user_id: uuid.UUID, role: str | None = None) -> int:
    filters = [Conversation.user_id == user_id]
    if role:
        filters.append(Message.role == role)
    return (
        db.scalar(
            select(func.count())
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(*filters)
        )
        or 0
    )


def add_citations(db: Session, message_id: uuid.UUID, citations: list[Citation]) -> None:
    for citation in citations:
        citation.message_id = message_id
    db.add_all(citations)


def get_message_owned(db: Session, message_id: uuid.UUID, user_id: uuid.UUID) -> Message | None:
    return db.scalar(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id, Conversation.user_id == user_id)
    )


def upsert_feedback(
    db: Session, *, message_id: uuid.UUID, user_id: uuid.UUID, rating: str, comment: str | None
) -> Feedback:
    existing = db.scalar(
        select(Feedback).where(Feedback.message_id == message_id, Feedback.user_id == user_id)
    )
    if existing:
        existing.rating = rating
        existing.comment = comment
        db.add(existing)
        return existing
    feedback = Feedback(message_id=message_id, user_id=user_id, rating=rating, comment=comment)
    db.add(feedback)
    return feedback
