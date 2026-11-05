"""Lightweight, dependency-free reranking.

A cross-encoder would improve ordering but adds a large model dependency. This
reranker rewards lexical coverage, exact phrase and heading matches, and numeric
agreement (insurance questions are often about days, percentages, and amounts).
"""

import re

from app.ai.text import tokenize
from app.ai.types import RetrievedChunk

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def rerank(results: list[RetrievedChunk], query: str) -> list[RetrievedChunk]:
    query_terms = set(tokenize(query))
    query_lower = " ".join(query.lower().split())
    query_numbers = set(NUMBER_RE.findall(query))
    if not results:
        return results

    for item in results:
        content = " ".join(item.content.lower().split())
        content_terms = set(tokenize(item.content))
        coverage = len(query_terms & content_terms) / len(query_terms) if query_terms else 0.0
        phrase = 1.0 if query_lower and query_lower in content else 0.0
        heading_terms = set(tokenize(item.heading))
        heading_match = len(query_terms & heading_terms) / len(query_terms) if query_terms else 0.0
        numbers = set(NUMBER_RE.findall(item.content))
        numeric_match = len(query_numbers & numbers) / len(query_numbers) if query_numbers else 0.0
        item.rerank_score = (
            0.5 * coverage + 0.2 * phrase + 0.2 * heading_match + 0.1 * numeric_match
        )
        # Reranking adjusts the fused score rather than replacing it, so the
        # lexical/semantic rank still dominates.
        item.score = 0.65 * item.score + 0.35 * item.rerank_score
    return results
