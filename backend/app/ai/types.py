"""Shared AI-layer data structures (independent of the database layer)."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
    extraction_method: str = "text"


@dataclass(frozen=True)
class ChunkDraft:
    ordinal: int
    content: str
    page_start: int
    page_end: int
    heading: str


@dataclass
class RetrievedChunk:
    """A chunk plus its retrieval scores. `ref` is the persistence object."""

    ref: object
    score: float
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rerank_score: float = 0.0
    rank: int = 0

    @property
    def page_start(self) -> int:
        return int(self.ref.page_start)  # type: ignore[attr-defined]

    @property
    def page_end(self) -> int:
        return int(self.ref.page_end)  # type: ignore[attr-defined]

    @property
    def content(self) -> str:
        return str(self.ref.content)  # type: ignore[attr-defined]

    @property
    def heading(self) -> str:
        return str(getattr(self.ref, "heading", "") or "")  # noqa: B009 - ref is a protocol


@dataclass(frozen=True)
class ValidatedCitation:
    source_id: str
    chunk_id: object
    page_start: int
    page_end: int
    quote: str
    is_valid: bool = True


@dataclass
class GroundedAnswer:
    answer_markdown: str
    citations: list[ValidatedCitation] = field(default_factory=list)
    confidence: float = 0.0
    insufficient_evidence: bool = False
    stated: list[str] = field(default_factory=list)
    inferred: list[str] = field(default_factory=list)
    not_in_document: list[str] = field(default_factory=list)
    citation_status: str = "missing"
    invalid_citations: int = 0
    metadata: dict = field(default_factory=dict)


class LLM(Protocol):
    model_name: str

    def stream(self, messages: list[dict[str, str]]) -> object:
        """Yield raw text deltas."""
        ...

    def complete(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str: ...
