from types import SimpleNamespace

import pytest
from app.ai.extraction import build_insight_payload, extract_with_rules
from app.ai.types import PageText
from app.services.comparison import build_payload

pytestmark = pytest.mark.unit

PAGE = PageText(
    page_number=1,
    text=(
        "INSURIO HEALTH POLICY SCHEDULE\n"
        "Policy Holder: Asha Rao\n"
        "Sum Insured: Rs. 500000\n"
        "EXCLUSIONS\n"
        "Cosmetic surgery.\n"
        "War and nuclear risks.\n"
    ),
)


def field(fields, key):
    return next(item for item in fields if item.key == key)


def test_rules_extract_values_with_evidence():
    fields = extract_with_rules([PAGE])

    sum_insured = field(fields, "sum_insured")
    assert sum_insured.status == "found"
    assert "500000" in sum_insured.value
    assert sum_insured.page == 1
    assert "Sum Insured" in sum_insured.quote

    exclusions = field(fields, "exclusions")
    assert exclusions.status == "found"
    assert "Cosmetic surgery" in exclusions.value
    assert exclusions.page == 1


def test_unstated_fields_are_marked_missing_not_guessed():
    fields = extract_with_rules([PAGE])
    maternity = field(fields, "maternity")
    assert maternity.status == "missing"
    assert maternity.value == ""
    assert maternity.confidence == 0.0


def test_payload_counts_and_metadata():
    payload, method, model = build_insight_payload([PAGE])
    assert method == "rules"
    assert model is None
    assert payload["meta"]["found"] > 0
    assert payload["meta"]["pages"] == 1
    assert len(payload["fields"]) > 10


def _insight(value: str, status: str = "found", page: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        payload={
            "fields": [
                {
                    "key": "sum_insured",
                    "label": "Sum insured",
                    "category": "coverage",
                    "value": value,
                    "quote": value,
                    "page": page,
                    "confidence": 0.8,
                    "status": status,
                }
            ]
        }
    )


def test_comparison_detects_differing_values():
    documents = [
        SimpleNamespace(id="11111111-1111-1111-1111-111111111111", original_filename="a.pdf"),
        SimpleNamespace(id="22222222-2222-2222-2222-222222222222", original_filename="b.pdf"),
    ]
    payload = build_payload(documents, [_insight("500000"), _insight("1000000")])

    assert payload["summary"]["fields_compared"] == 1
    assert payload["summary"]["differences"] == 1
    assert payload["fields"][0]["differs"] is True


def test_comparison_reports_missing_information():
    documents = [
        SimpleNamespace(id="11111111-1111-1111-1111-111111111111", original_filename="a.pdf"),
        SimpleNamespace(id="22222222-2222-2222-2222-222222222222", original_filename="b.pdf"),
    ]
    payload = build_payload(documents, [_insight("500000"), _insight("", "missing")])

    assert payload["fields"][0]["differs"] is True
    assert payload["fields"][0]["missing_in"] == ["22222222-2222-2222-2222-222222222222"]
