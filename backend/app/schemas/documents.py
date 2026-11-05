"""Document, job, and insight response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    progress: int
    detail: str
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    page_count: int
    chunk_count: int
    size_bytes: int
    error_message: str | None = None
    has_insights: bool = False
    created_at: datetime
    processed_at: datetime | None = None

    @classmethod
    def from_model(cls, document, *, has_insights: bool = False) -> "DocumentOut":
        return cls(
            id=document.id,
            filename=document.original_filename,
            status=document.status,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            size_bytes=document.size_bytes,
            error_message=document.error_message,
            has_insights=has_insights,
            created_at=document.created_at,
            processed_at=document.processed_at,
        )


class DocumentDetail(DocumentOut):
    latest_job: JobOut | None = None


class DocumentStatusOut(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None = None
    page_count: int
    chunk_count: int
    job: JobOut | None = None


class PageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str
    char_count: int
    extraction_method: str


class InsightFieldOut(BaseModel):
    key: str
    label: str
    category: str
    value: str
    quote: str
    page: int | None = None
    confidence: float
    status: str


class InsightOut(BaseModel):
    document_id: uuid.UUID
    filename: str
    fields: list[InsightFieldOut]
    meta: dict[str, Any]
    extraction_method: str
    llm_model: str | None = None
    updated_at: datetime


class ComparisonCreateRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=2, max_length=5)
    title: str | None = Field(default=None, max_length=200)


class ComparisonDocumentOut(BaseModel):
    id: uuid.UUID
    filename: str


class ComparisonFieldValue(BaseModel):
    document_id: uuid.UUID
    value: str
    status: str
    page: int | None = None
    quote: str = ""
    confidence: float = 0.0


class ComparisonFieldOut(BaseModel):
    key: str
    label: str
    category: str
    values: list[ComparisonFieldValue]
    differs: bool
    missing_in: list[uuid.UUID]


class ComparisonOut(BaseModel):
    id: uuid.UUID
    title: str
    document_ids: list[uuid.UUID]
    documents: list[ComparisonDocumentOut]
    fields: list[ComparisonFieldOut]
    summary: dict[str, int]
    created_at: datetime
