"""Shared response schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str


class MetaResponse(BaseModel):
    app_version: str
    environment: str
    llm_configured: bool
    llm_model: str
    embeddings_mode: str
    ocr_enabled: bool
    max_upload_mb: int
    max_pdf_pages: int
    retrieval_top_k: int


class HealthResponse(BaseModel):
    status: str
    database: str = "unknown"
    version: str


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")
