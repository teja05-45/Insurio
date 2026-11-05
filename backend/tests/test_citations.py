import uuid
from types import SimpleNamespace

from app.ai.citations import validate_citations
from app.ai.pipeline import build_grounded_answer, parse_json_object
from app.ai.types import RetrievedChunk

SOURCE_TEXT = "Cosmetic surgery is excluded from coverage unless required after an accident."


def make_source(text: str = SOURCE_TEXT, page: int = 4) -> RetrievedChunk:
    ref = SimpleNamespace(
        id=uuid.uuid4(), content=text, page_start=page, page_end=page, heading="Exclusions"
    )
    return RetrievedChunk(ref=ref, score=1.0)


def test_verbatim_quote_is_accepted():
    citations, invalid = validate_citations(
        [{"source_id": "S1", "quote": "Cosmetic surgery is excluded from coverage"}],
        [make_source()],
    )
    assert invalid == 0
    assert len(citations) == 1
    assert citations[0].page_start == 4
    assert citations[0].chunk_id is not None


def test_punctuation_and_case_differences_still_match():
    citations, _ = validate_citations(
        [{"source_id": "S1", "quote": "COSMETIC SURGERY, is excluded!"}], [make_source()]
    )
    assert len(citations) == 1


def test_invented_quote_is_rejected():
    citations, invalid = validate_citations(
        [{"source_id": "S1", "quote": "Dental implants are covered worldwide"}], [make_source()]
    )
    assert citations == []
    assert invalid == 1


def test_unknown_source_id_is_rejected():
    citations, invalid = validate_citations(
        [{"source_id": "S9", "quote": "Cosmetic surgery is excluded"}], [make_source()]
    )
    assert citations == []
    assert invalid == 1


def test_quote_shorter_than_the_minimum_is_rejected():
    # "cosm" exists verbatim in the source, so only the length rule can reject it.
    citations, invalid = validate_citations(
        [{"source_id": "S1", "quote": "cosm"}], [make_source()]
    )
    assert citations == []
    assert invalid == 1


def test_grounded_answer_flags_missing_citations():
    answer = build_grounded_answer(
        '{"answer_markdown": "It is excluded.", "citations": [], "confidence": 0.7}',
        [make_source()],
    )
    assert answer.answer_markdown == "It is excluded."
    assert answer.citation_status == "missing"
    assert answer.confidence == 0.7


def test_insufficient_evidence_answer_has_no_citation_requirement():
    answer = build_grounded_answer(
        '{"answer_markdown": "Not stated.", "insufficient_evidence": true, "citations": []}',
        [make_source()],
    )
    assert answer.insufficient_evidence is True
    assert answer.citation_status == "not_applicable"


def test_unparseable_output_is_surfaced_as_text_and_flagged():
    answer = build_grounded_answer("The policy excludes cosmetic surgery.", [make_source()])
    assert answer.answer_markdown == "The policy excludes cosmetic surgery."
    assert answer.citation_status == "unparsed"


def test_parse_json_object_handles_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object("not json") == {}
