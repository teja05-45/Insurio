"""Small shared text utilities for retrieval and reranking."""

import re

TOKEN_RE = re.compile(r"[a-z][a-z0-9]{1,}")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "that", "this", "these", "those",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "done", "have", "has",
    "had", "will", "would", "can", "could", "should", "may", "might", "must", "shall", "to", "of",
    "in", "on", "at", "for", "with", "by", "from", "as", "into", "about", "over", "under", "it",
    "its", "my", "me", "i", "we", "our", "you", "your", "they", "their", "he", "she", "his", "her",
    "what", "which", "who", "whom", "how", "when", "where", "why", "any", "all", "there", "here",
    "not", "no", "yes", "also", "per", "please", "tell", "know", "want", "need",
}


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]
