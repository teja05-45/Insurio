"""Conversation, message, citation, feedback, and usage schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreateRequest(BaseModel):
    document_id: uuid.UUID
    title: str | None = Field(default=None, max_length=200)


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def _clean(cls, value: str) -> str:
        return value.strip()


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    page_start: int
    page_end: int
    quote: str
    is_valid: bool


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    status: str
    citations: list[CitationOut] = Field(default_factory=list)
    confidence: float | None = None
    insufficient_evidence: bool = False
    citation_status: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    # Evidence split, persisted in metadata_json so it survives a reload.
    stated: list[str] = Field(default_factory=list)
    inferred: list[str] = Field(default_factory=list)
    not_in_document: list[str] = Field(default_factory=list)

    @classmethod
    def from_model(cls, message) -> "MessageOut":
        metadata = message.metadata_json or {}

        def _items(key: str) -> list[str]:
            value = metadata.get(key)
            if not isinstance(value, list):
                return []
            return [str(item) for item in value if str(item).strip()]

        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            status=message.status,
            citations=[CitationOut.model_validate(citation) for citation in message.citations],
            confidence=message.confidence,
            insufficient_evidence=message.insufficient_evidence,
            citation_status=message.citation_status,
            model=message.model,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
            stated=_items("stated"),
            inferred=_items("inferred"),
            not_in_document=_items("not_in_document"),
        )


class ConversationOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str | None = None
    title: str
    last_activity_at: datetime | None = None
    created_at: datetime
    message_count: int = 0
    preview: str | None = None


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def _clean(cls, value: str) -> str:
        return value.strip()


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)


class UsageSummary(BaseModel):
    documents: int
    conversations: int
    questions: int
    comparisons: int
    quota: int
    quota_used_percent: float
