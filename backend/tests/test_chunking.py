import re

import pytest
from app.ai.chunking import chunk_pages, is_heading, normalize_text
from app.ai.types import PageText

pytestmark = pytest.mark.unit


def test_heading_detection():
    assert is_heading("EXCLUSIONS")
    assert is_heading("3. Waiting Period")
    assert is_heading("Claim Procedure:")
    assert not is_heading("The policy covers hospitalisation expenses for the insured.")


def test_chunks_keep_page_and_heading_provenance():
    pages = [
        PageText(
            page_number=1,
            text=(
                "COVERAGE\n" + "Hospitalisation expenses are payable up to the sum insured. " * 12
            ),
        ),
        PageText(
            page_number=2,
            text=(
                "EXCLUSIONS\n"
                "Cosmetic surgery is excluded from coverage unless medically required."
            ),
        ),
    ]
    chunks = chunk_pages(pages, max_chars=300, overlap_chars=40)

    assert chunks
    assert all(chunk.page_start <= chunk.page_end for chunk in chunks)
    assert all(1 <= chunk.page_start <= 2 for chunk in chunks)
    assert all(chunk.content.strip() for chunk in chunks)
    assert any(chunk.heading == "EXCLUSIONS" for chunk in chunks)
    assert max(chunk.page_end for chunk in chunks) == 2


def test_chunks_contain_no_duplicate_bodies():
    pages = [
        PageText(
            page_number=1,
            text="The deductible is Rs. 10000. The deductible is Rs. 10000.",
        )
    ]
    chunks = chunk_pages(pages)
    fingerprints = [re.sub(r"\W+", "", chunk.content.lower()) for chunk in chunks]
    assert len(fingerprints) == len(set(fingerprints))


def test_normalize_text_collapses_whitespace():
    assert normalize_text("A  clause\r\n\r\n\r\nwith   spaces") == "A clause\n\nwith spaces"
