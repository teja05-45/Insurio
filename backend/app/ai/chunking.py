"""Page-aware, heading-aware chunking.

The original implementation concatenated every page into one string and chunked
characters, which lost page provenance. Here each sentence carries its page and
the current heading, and chunks are packed from those units. Every chunk keeps a
page range and heading, which is what makes citation validation possible.
"""

import hashlib
import re

from app.ai.types import ChunkDraft, PageText

WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9(\[•\-])")
NUMBERED_HEADING_RE = re.compile(
    r"^(?:section|part|article|clause|schedule|annexure|appendix)\b|^\d+(?:\.\d+)*[.)]?\s+\S",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"^\s*(?:[-•*·]|\(?\d+[.)]|[a-z][.)])\s+", re.IGNORECASE)

# Common insurance headings that appear without numbering or capitals.
KNOWN_HEADINGS = {
    "coverage",
    "coverages",
    "benefits",
    "exclusions",
    "waiting period",
    "waiting periods",
    "definitions",
    "deductible",
    "co-payment",
    "copayment",
    "claims",
    "claim procedure",
    "how to claim",
    "pre-existing diseases",
    "maternity",
    "renewal",
    "terms and conditions",
    "sum insured",
    "policy schedule",
    "general conditions",
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = WHITESPACE_RE.sub(" ", text)
    text = MULTI_NEWLINE_RE.sub("\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def is_heading(line: str) -> bool:
    candidate = line.strip().rstrip(":").strip()
    if not candidate or len(candidate) > 120:
        return False
    if candidate.lower() in KNOWN_HEADINGS:
        return True
    if NUMBERED_HEADING_RE.match(line.strip()) and len(candidate.split()) <= 12:
        return True
    letters = [c for c in candidate if c.isalpha()]
    words = candidate.split()
    if len(words) <= 9 and not candidate.endswith(".") and letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio >= 0.75:
            return True
    return bool(candidate.endswith(":") and 2 <= len(words) <= 8)


def _units_for_page(page: PageText) -> list[tuple[str, int, str]]:
    """Return (text, page, heading) sentence units for one page."""
    units: list[tuple[str, int, str]] = []
    heading = ""
    for raw_line in normalize_text(page.text).split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if is_heading(line):
            heading = line.rstrip(":").strip()[:300]
            continue
        # Bullets are independent clauses; keep them whole where possible.
        if BULLET_RE.match(line):
            units.append((line, page.page_number, heading))
            continue
        for sentence in SENTENCE_SPLIT_RE.split(line):
            sentence = sentence.strip()
            if sentence:
                units.append((sentence, page.page_number, heading))
    return units


def _split_long_unit(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    parts: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            parts.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        parts.append(current)
    return parts


def chunk_pages(
    pages: list[PageText],
    *,
    max_chars: int = 1200,
    overlap_chars: int = 180,
    min_chars: int = 20,
) -> list[ChunkDraft]:
    """Pack page/section-aware units into overlapping chunks with provenance."""
    units: list[tuple[str, int, str]] = []
    for page in pages:
        units.extend(_units_for_page(page))
    if not units:
        return []

    drafts: list[ChunkDraft] = []
    seen: set[str] = set()
    current: list[tuple[str, int, str]] = []
    current_len = 0

    def flush(*, carry_overlap: bool = True) -> None:
        nonlocal current, current_len
        if not current:
            return
        body = " ".join(u[0] for u in current).strip()
        heading = current[0][2] or ""
        content = f"{heading}\n{body}".strip() if heading else body
        page_start = min(u[1] for u in current)
        page_end = max(u[1] for u in current)
        fingerprint = hashlib.sha256(re.sub(r"\W+", "", body.lower()).encode()).hexdigest()
        if len(body) >= min_chars and fingerprint not in seen:
            seen.add(fingerprint)
            drafts.append(
                ChunkDraft(
                    ordinal=len(drafts),
                    content=content,
                    page_start=page_start,
                    page_end=page_end,
                    heading=heading,
                )
            )
        # Carry a single short tail unit as overlap for continuity, but never
        # across a heading change: that would mislabel the next section.
        tail = (
            [current[-1]]
            if carry_overlap and current and len(current[-1][0]) <= overlap_chars
            else []
        )
        current = tail
        current_len = sum(len(u[0]) + 1 for u in tail)

    for unit_text, page, heading in units:
        # A new section is a semantic boundary: never merge two headings into
        # one chunk, otherwise the heading metadata would be misleading.
        if current and heading != current[0][2]:
            flush(carry_overlap=False)
        for piece in _split_long_unit(unit_text, max_chars):
            piece_len = len(piece) + 1
            if current and current_len + piece_len > max_chars:
                flush()
            current.append((piece, page, heading))
            current_len += piece_len

    flush()
    # Re-number after deduplication.
    return [
        ChunkDraft(
            ordinal=i,
            content=d.content,
            page_start=d.page_start,
            page_end=d.page_end,
            heading=d.heading,
        )
        for i, d in enumerate(drafts)
    ]
