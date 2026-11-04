"""Server-side citation validation.

A citation is accepted only if its source id was actually supplied to the model
and its quote appears verbatim (whitespace/punctuation-insensitive) in that
source's retrieved text. This is the main defence against fabricated clauses.
"""

import re

from app.ai.types import RetrievedChunk, ValidatedCitation

MIN_QUOTE_CHARS = 6
MAX_QUOTE_CHARS = 600
_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_for_match(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", text.lower()).strip()


def validate_citations(
    raw_citations: object, sources: list[RetrievedChunk]
) -> tuple[list[ValidatedCitation], int]:
    if not isinstance(raw_citations, list):
        return [], 0

    source_map: dict[str, RetrievedChunk] = {
        f"S{index}": source for index, source in enumerate(sources, start=1)
    }
    accepted: list[ValidatedCitation] = []
    invalid = 0
    seen: set[tuple[str, str]] = set()

    for item in raw_citations:
        if not isinstance(item, dict):
            invalid += 1
            continue
        source_id = str(item.get("source_id", "")).strip().upper()
        quote = str(item.get("quote", "")).strip()
        source = source_map.get(source_id)
        if source is None or len(quote) < MIN_QUOTE_CHARS:
            invalid += 1
            continue
        quote = quote[:MAX_QUOTE_CHARS]
        normalized_quote = normalize_for_match(quote)
        if not normalized_quote or normalized_quote not in normalize_for_match(source.content):
            invalid += 1
            continue
        key = (source_id, normalized_quote)
        if key in seen:
            continue
        seen.add(key)
        accepted.append(
            ValidatedCitation(
                source_id=source_id,
                chunk_id=getattr(source.ref, "id", None),
                page_start=source.page_start,
                page_end=source.page_end,
                quote=quote,
                is_valid=True,
            )
        )
    return accepted, invalid
