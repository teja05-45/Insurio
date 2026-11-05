"""Document, page, chunk, and processing-job models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk

DOCUMENT_STATUSES = ("queued", "processing", "ready", "failed")
JOB_STATUSES = ("queued", "processing", "ready", "failed")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.ordinal",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','processing','ready','failed')",
            name="document_status",
        ),
        Index("ix_documents_user_created", "user_id", "created_at"),
        Index("ix_documents_user_sha", "user_id", "sha256"),
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False, default="text")

    document: Mapped[Document] = relationship(back_populates="pages")

    __table_args__ = (UniqueConstraint("document_id", "page_number", name="document_page"),)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120))

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "ordinal", name="document_chunk_ordinal"),
        Index("ix_document_chunks_doc_page", "document_id", "page_start"),
    )


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="ingest")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','processing','ready','failed')",
            name="job_status",
        ),
        Index("ix_processing_jobs_document_created", "document_id", "created_at"),
    )
