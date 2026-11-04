"""Structured policy insight and comparison models."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class PolicyInsight(Base, TimestampMixin):
    __tablename__ = "policy_insights"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(40), nullable=False, default="rules")
    llm_model: Mapped[str | None] = mapped_column(String(120))

    __table_args__ = (Index("ix_policy_insights_document", "document_id"),)


class PolicyComparison(Base, TimestampMixin):
    __tablename__ = "policy_comparisons"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="Policy comparison")
    document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_policy_comparisons_user_created", "user_id", "created_at"),)
