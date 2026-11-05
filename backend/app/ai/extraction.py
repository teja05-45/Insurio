"""Deterministic policy-field extraction with source evidence.

Rules always run. LLM enrichment is optional and only accepted when its quoted
evidence is found verbatim on the stated page. A field that is not stated in the
document is returned as `missing`, never guessed.
"""

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.ai.chunking import is_heading, normalize_text
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT
from app.ai.types import LLM, PageText
from app.core.logging import get_logger

logger = get_logger("insurio.extraction")
NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class ExtractedField:
    key: str
    label: str
    category: str
    value: str
    quote: str
    page: int | None
    confidence: float
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    category: str
    keywords: tuple[str, ...]
    pattern: str | None = None
    aggregate_headings: tuple[str, ...] = ()
    list_mode: bool = False


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "policyholder",
        "Policyholder",
        "policy",
        ("policy holder", "policyholder", "proposer", "insured name"),
        r"(?:policy\s*holder|policyholder|proposer|insured\s*name)\s*[:\-]\s*(.{2,90})",
    ),
    FieldSpec(
        "insurer",
        "Insurer",
        "policy",
        ("insurer", "insurance company", "underwritten by"),
        r"(?:insurer|insurance\s+company|underwritten\s+by)\s*[:\-]\s*(.{2,90})",
    ),
    FieldSpec(
        "policy_number",
        "Policy number",
        "policy",
        ("policy no", "policy number", "certificate no"),
        r"(?:policy\s*(?:no|number)|certificate\s*no)\s*[.:#\-]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{3,40})",
    ),
    FieldSpec(
        "policy_type",
        "Policy type",
        "policy",
        ("policy type", "plan type", "product name"),
        r"(?:policy|plan|product)\s*(?:type|name)\s*[:\-]\s*(.{2,80})",
    ),
    FieldSpec(
        "insured_members",
        "Insured members",
        "policy",
        ("insured members", "members covered", "persons insured", "family members"),
        r"(?:insured\s+members|members\s+covered|persons\s+insured|family\s+members)\s*[:\-]\s*(.{2,160})",
    ),
    FieldSpec(
        "sum_insured",
        "Sum insured",
        "coverage",
        ("sum insured", "sum assured", "coverage amount"),
        r"(?:sum\s+(?:insured|assured)|coverage\s+amount)\s*(?:of|is|:)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)",
    ),
    FieldSpec(
        "deductibles",
        "Deductible",
        "coverage",
        ("deductible", "excess"),
        r"deductible[^\n]{0,80}?(?:rs\.?|inr|₹)?\s*([\d,]+|nil)",
        list_mode=False,
    ),
    FieldSpec(
        "co_payment", "Co-payment", "coverage", ("co-payment", "co payment", "copayment", "co-pay")
    ),
    FieldSpec("room_rent_limit", "Room rent limit", "coverage", ("room rent",)),
    FieldSpec(
        "disease_sub_limits",
        "Disease sub-limits",
        "coverage",
        ("sub-limit", "sub limit", "per disease limit", "disease wise"),
    ),
    FieldSpec(
        "waiting_periods",
        "Waiting periods",
        "conditions",
        ("waiting period", "initial waiting", "pre-existing waiting"),
    ),
    FieldSpec(
        "pre_existing_disease",
        "Pre-existing disease terms",
        "conditions",
        ("pre-existing", "pre existing", "ped"),
    ),
    FieldSpec("maternity", "Maternity", "coverage", ("maternity", "pregnancy", "childbirth")),
    FieldSpec("renewal_conditions", "Renewal conditions", "conditions", ("renewal",)),
    FieldSpec("grace_period", "Grace period", "conditions", ("grace period",)),
    FieldSpec(
        "coverage",
        "Coverage",
        "coverage",
        (),
        aggregate_headings=("coverage", "benefits", "what is covered"),
        list_mode=True,
    ),
    FieldSpec(
        "exclusions",
        "Exclusions",
        "exclusions",
        (),
        aggregate_headings=("exclusion", "not covered", "what is not covered"),
        list_mode=True,
    ),
    FieldSpec(
        "claim_procedure",
        "Claim procedure",
        "claims",
        ("claim procedure", "how to claim", "claim process", "notify the insurer"),
        aggregate_headings=("claim procedure", "how to claim", "claims procedure", "claim process"),
    ),
    FieldSpec(
        "claim_documents",
        "Claim documents",
        "claims",
        ("documents required", "claim documents", "documents to be submitted"),
        aggregate_headings=("documents required", "claim documents"),
    ),
    FieldSpec(
        "important_conditions",
        "Important conditions",
        "conditions",
        (),
        aggregate_headings=("general conditions", "terms and conditions", "important conditions"),
        list_mode=True,
    ),
)

FIELD_LABELS = {spec.key: spec.label for spec in FIELDS}


def normalize_for_match(text: str) -> str:
    return NORMALIZE_RE.sub(" ", text.lower()).strip()


def _clean(value: str, limit: int = 400) -> str:
    return re.sub(r"\s+", " ", value).strip(" :;-")[:limit]


def _sentences(pages: list[PageText]) -> list[tuple[int, str]]:
    output: list[tuple[int, str]] = []
    for page in pages:
        for line in normalize_text(page.text).split("\n"):
            line = line.strip()
            if not line or is_heading(line):
                continue
            # Do not split after abbreviations such as "Rs." or "No.": the
            # next token is a digit, not a new sentence.
            for sentence in re.split(r"(?<=[.;!?])\s+(?=[A-Z(\[•])", line):
                if len(sentence.strip()) > 2:
                    output.append((page.page_number, sentence.strip()))
    return output


def _aggregate(pages: list[PageText], spec: FieldSpec) -> ExtractedField | None:
    if not spec.aggregate_headings:
        return None
    collecting = False
    items: list[tuple[int, str]] = []
    current_page = None
    for page in pages:
        for line in normalize_text(page.text).split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower().rstrip(":")
            if is_heading(stripped):
                collecting = any(head in lower for head in spec.aggregate_headings)
                if collecting:
                    current_page = page.page_number
                continue
            if collecting and current_page is not None:
                if stripped.endswith(":") or len(stripped) < 4:
                    continue
                items.append((current_page, stripped))
                if len(items) >= 10:
                    break
        if len(items) >= 10:
            break
    if not items:
        return None
    if spec.list_mode:
        value = "; ".join(item[1].rstrip(".;") for item in items[:8])[:600]
        quote = "\n".join(item[1] for item in items[:4])[:600]
    else:
        value = _clean(" ".join(item[1] for item in items[:4]), 600)
        quote = value
    return ExtractedField(
        key=spec.key,
        label=spec.label,
        category=spec.category,
        value=value,
        quote=quote,
        page=items[0][0],
        confidence=0.7,
        status="found" if value else "missing",
    )


def _scalar(sentences: list[tuple[int, str]], spec: FieldSpec) -> ExtractedField:
    # (page, quote, confidence, extracted value)
    matches: list[tuple[int, str, float, str]] = []
    if spec.pattern:
        regex = re.compile(spec.pattern, re.IGNORECASE)
        for page, sentence in sentences:
            match = regex.search(sentence)
            if match:
                value = _clean(match.group(1))
                if value:
                    matches.append((page, sentence[:500], 0.82, value))
                    break

    if not matches:
        for page, sentence in sentences:
            lower = sentence.lower()
            if any(keyword in lower for keyword in spec.keywords):
                matches.append((page, sentence[:500], 0.58, _clean(sentence, 300)))
                if len(matches) >= 3:
                    break

    if not matches:
        return ExtractedField(spec.key, spec.label, spec.category, "", "", None, 0.0, "missing")

    page, quote, confidence, value = matches[0]
    distinct = {normalize_for_match(match[3]) for match in matches}
    status = "found"
    if len(distinct) > 1 and spec.key in {"sum_insured", "deductibles"}:
        value = " / ".join(match[3] for match in matches[:3])
        status = "ambiguous"
        confidence = 0.45
    return ExtractedField(
        spec.key, spec.label, spec.category, value, quote, page, confidence, status
    )


def extract_with_rules(pages: list[PageText]) -> list[ExtractedField]:
    sentences = _sentences(pages)
    results: list[ExtractedField] = []
    for spec in FIELDS:
        aggregate = _aggregate(pages, spec) if spec.aggregate_headings else None
        if aggregate is not None:
            results.append(aggregate)
            continue
        results.append(_scalar(sentences, spec))
    return results


def _validate_llm_field(
    key: str, item: object, pages_by_number: dict[int, str], spec: FieldSpec
) -> ExtractedField | None:
    if not isinstance(item, dict):
        return None
    quote = _clean(str(item.get("quote", "")), 600)
    value = _clean(str(item.get("value", "")), 600)
    status = str(item.get("status", "found")).lower()
    try:
        page = int(item.get("page", 0))
        confidence = max(0.0, min(0.9, float(item.get("confidence", 0.6))))
    except (TypeError, ValueError):
        return None
    if status not in {"found", "ambiguous", "missing"}:
        return None
    if status == "missing":
        return ExtractedField(spec.key, spec.label, spec.category, "", "", None, 0.0, "missing")
    page_text = pages_by_number.get(page)
    if not value or not quote or page_text is None:
        return None
    if normalize_for_match(quote) not in normalize_for_match(page_text):
        return None
    return ExtractedField(
        spec.key, spec.label, spec.category, value, quote, page, confidence, status
    )


def enrich_with_llm(
    pages: list[PageText], rules: list[ExtractedField], llm: LLM, model_name: str
) -> list[ExtractedField]:
    """Merge LLM values only when their quote is verifiable on the given page."""
    pages_by_number = {page.page_number: page.text for page in pages}
    budget = 18_000
    blocks: list[str] = []
    used = 0
    for page in pages:
        text = normalize_text(page.text)[:1_200]
        if not text:
            continue
        block = f"[Page {page.page_number}]\n{text}"
        if used + len(block) > budget:
            break
        blocks.append(block)
        used += len(block)
    if not blocks:
        return rules

    user_prompt = (
        "Fields to extract:\n"
        + "\n".join(f"- {spec.key}: {spec.label}" for spec in FIELDS)
        + "\n\nDocument text:\n"
        + "\n\n".join(blocks)
    )
    try:
        raw = llm.complete(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
        )
    except Exception:
        logger.warning("insight_enrichment_failed", extra={"event": "insight_enrichment_failed"})
        return rules

    from app.ai.pipeline import parse_json_object

    data = parse_json_object(raw)
    if not data:
        return rules

    by_key = {field.key: field for field in rules}
    for spec in FIELDS:
        candidate = _validate_llm_field(spec.key, data.get(spec.key), pages_by_number, spec)
        if candidate is None:
            continue
        existing = by_key[spec.key]
        if candidate.status != "missing" and (
            existing.status == "missing" or candidate.confidence >= existing.confidence
        ):
            by_key[spec.key] = candidate
    return [by_key[spec.key] for spec in FIELDS]


def build_insight_payload(
    pages: list[PageText],
    *,
    llm: LLM | None = None,
    use_llm: bool = False,
    model_name: str = "",
) -> tuple[dict, str, str | None]:
    rules = extract_with_rules(pages)
    method = "rules"
    used_model: str | None = None
    if use_llm and llm is not None:
        rules = enrich_with_llm(pages, rules, llm, model_name)
        method = "rules+llm"
        used_model = model_name

    fields = [field.to_dict() for field in rules]
    counts = {
        "found": sum(1 for field in fields if field["status"] == "found"),
        "ambiguous": sum(1 for field in fields if field["status"] == "ambiguous"),
        "missing": sum(1 for field in fields if field["status"] == "missing"),
    }
    payload = {
        "fields": fields,
        "meta": {
            "pages": len(pages),
            "extracted_at": datetime.now(UTC).isoformat(),
            "method": method,
            "llm_model": used_model,
            **counts,
        },
    }
    return payload, method, used_model
