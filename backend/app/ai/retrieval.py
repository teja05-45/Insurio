"""Hybrid retrieval: BM25 + cosine similarity fused with reciprocal rank fusion."""

import math
from collections import Counter

from app.ai.embeddings import Embedder
from app.ai.rerank import rerank
from app.ai.text import tokenize
from app.ai.types import RetrievedChunk


class BM25:
    """Okapi BM25 over an in-memory chunk corpus."""

    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(document) for document in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_length = (sum(self.doc_lengths) / len(self.doc_lengths)) if self.doc_lengths else 0
        self.term_frequencies = [Counter(tokens) for tokens in self.doc_tokens]
        document_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            document_frequency.update(set(tokens))
        total = len(self.doc_tokens)
        self.idf = {
            term: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def scores(self, query: str) -> list[float]:
        query_terms = tokenize(query)
        results: list[float] = []
        for index, frequencies in enumerate(self.term_frequencies):
            length = self.doc_lengths[index]
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * (length / self.avg_length if self.avg_length else 0)
                )
                score += self.idf.get(term, 0.0) * (frequency * (self.k1 + 1)) / denominator
            results.append(score)
        return results


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize(scores: list[float]) -> list[float]:
    top = max(scores) if scores else 0.0
    if top <= 0:
        return [0.0 for _ in scores]
    return [score / top for score in scores]


def retrieve(
    chunks: list[object],
    query: str,
    *,
    embedder: Embedder | None = None,
    top_k: int = 6,
    candidates: int = 24,
    min_score: float = 0.0,
) -> tuple[list[RetrievedChunk], str]:
    """Return ranked chunks and the retrieval mode used for this query."""
    if not chunks or not query.strip():
        return [], "none"

    contents = [str(getattr(chunk, "content", "")) for chunk in chunks]
    bm25 = BM25(contents)
    bm25_scores = bm25.scores(query)
    bm25_norm = _normalize(bm25_scores)

    vector_scores: list[float] = [0.0] * len(chunks)
    mode = "bm25"
    if embedder is not None:
        embedded = [chunk for chunk in chunks if getattr(chunk, "embedding", None)]
        if embedded:
            query_vector = embedder.embed_query(query)
            vector_scores = [
                cosine(list(chunk.embedding), query_vector)  # type: ignore[attr-defined]
                if getattr(chunk, "embedding", None)
                else 0.0
                for chunk in chunks
            ]
            mode = "hybrid"

    # Candidate pool from both retrievers.
    bm25_order = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)[:candidates]
    vector_order = sorted(range(len(chunks)), key=lambda i: vector_scores[i], reverse=True)[
        :candidates
    ]
    pool = set(bm25_order) | set(vector_order)
    bm25_rank = {index: rank for rank, index in enumerate(bm25_order)}
    vector_rank = {index: rank for rank, index in enumerate(vector_order)}

    results: list[RetrievedChunk] = []
    for index in pool:
        rrf = 0.0
        if index in bm25_rank:
            rrf += 1.0 / (60 + bm25_rank[index] + 1)
        if embedder is not None and index in vector_rank:
            rrf += 1.0 / (60 + vector_rank[index] + 1)
        results.append(
            RetrievedChunk(
                ref=chunks[index],
                score=rrf,
                bm25_score=bm25_norm[index],
                vector_score=max(0.0, vector_scores[index]),
            )
        )

    top_rrf = max((item.score for item in results), default=0.0)
    for item in results:
        item.score = item.score / top_rrf if top_rrf else 0.0

    results = rerank(results, query)
    results = [item for item in results if item.score > min_score]

    # Never return chunks that matched neither lexically nor semantically.
    results = [
        item
        for item in results
        if item.bm25_score > 0 or item.vector_score >= 0.25 or item.rerank_score > 0
    ]
    results.sort(key=lambda item: item.score, reverse=True)
    results = results[:top_k]
    for rank, item in enumerate(results, 1):
        item.rank = rank
    return results, mode
