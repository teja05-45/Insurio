import uuid
from types import SimpleNamespace

from app.ai.embeddings import HashingEmbedder
from app.ai.retrieval import retrieve

DOCUMENTS = [
    "Cosmetic surgery is excluded from coverage unless required after an injury.",
    "Hospitalisation expenses are covered up to the sum insured of Rs. 500000.",
    "The policy renews annually and a grace period of 30 days applies.",
]


def make_chunks(with_embeddings: bool = False) -> list[SimpleNamespace]:
    embedder = HashingEmbedder(384)
    vectors = embedder.embed_documents(DOCUMENTS)
    return [
        SimpleNamespace(
            id=uuid.uuid4(),
            content=text,
            page_start=index + 1,
            page_end=index + 1,
            heading="",
            embedding=vectors[index] if with_embeddings else None,
        )
        for index, text in enumerate(DOCUMENTS)
    ]


def test_bm25_only_ranks_the_relevant_chunk_first():
    results, mode = retrieve(make_chunks(), "Is cosmetic surgery covered?")
    assert mode == "bm25"
    assert results
    assert results[0].page_start == 1


def test_hybrid_mode_uses_embeddings_when_available():
    embedder = HashingEmbedder(384)
    results, mode = retrieve(
        make_chunks(with_embeddings=True),
        "Is cosmetic surgery covered?",
        embedder=embedder,
    )
    assert mode == "hybrid"
    assert results[0].page_start == 1
    assert results[0].vector_score >= 0


def test_empty_query_returns_nothing():
    results, mode = retrieve(make_chunks(), "   ")
    assert results == []
    assert mode == "none"


def test_results_respect_top_k():
    results, _ = retrieve(make_chunks(), "policy", top_k=1)
    assert len(results) == 1
    assert results[0].rank == 1
