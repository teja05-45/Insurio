"""Conversation, message, citation, and feedback models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk

MESSAGE_ROLES = ("user", "assistant")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New conversation")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (Index("ix_conversations_user_activity", "user_id", "last_activity_at"),)


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="complete")
    model: Mapped[str | None] = mapped_column(String(120))
    retrieval_mode: Mapped[str | None] = mapped_column(String(40))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    insufficient_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    citation_status: Mapped[str | None] = mapped_column(String(30))
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="Citation.page_start",
    )

    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="message_role"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = uuid_pk()
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL")
    )
    source_id: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    message: Mapped[Message] = relationship(back_populates="citations")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))

    __table_args__ = (
        CheckConstraint("rating IN ('up','down')", name="feedback_rating"),
        UniqueConstraint("message_id", "user_id", name="feedback_message_user"),
    )
