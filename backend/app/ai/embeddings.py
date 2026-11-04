"""Embedding providers with explicit, visible degradation.

Order of preference in `auto` mode: fastembed (ONNX, no torch), then
sentence-transformers, then disabled. A deterministic hashing embedder exists for
tests and offline development; it is never selected automatically because it is a
lexical surrogate, not a semantic model.
"""

import hashlib
import importlib.util
import math
import re
from functools import lru_cache
from typing import Protocol

from app.core.config import Settings

TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder(Protocol):
    name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class HashingEmbedder:
    """Deterministic signed feature hashing over words and character trigrams."""

    name = "hashing"
    dimensions = 384

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def _features(self, text: str) -> list[str]:
        words = TOKEN_RE.findall(text.lower())
        features = [f"w:{word}" for word in words]
        for word in words:
            padded = f"^{word}$"
            features.extend(f"c:{padded[i : i + 3]}" for i in range(max(1, len(padded) - 2)))
        return features

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % self.dimensions
            sign = 1.0 if (value >> 63) & 1 else -1.0
            vector[index] += sign
        return _l2_normalize(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbedder:
    name = "fastembed"

    def __init__(self, model_name: str) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)
        self.model_name = model_name
        self.dimensions = 384

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, vector)) for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class SentenceTransformerEmbedder:
    name = "sentence-transformers"

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def embedding_mode(settings: Settings) -> str:
    """Report what would be used, without loading a model."""
    if not settings.EMBEDDINGS_ENABLED or settings.EMBEDDING_PROVIDER == "none":
        return "disabled"
    provider = settings.EMBEDDING_PROVIDER
    if provider == "hashing":
        return "hashing"
    if provider in ("auto", "fastembed") and _module_available("fastembed"):
        return "fastembed"
    if provider in ("auto", "sentence-transformers") and _module_available("sentence_transformers"):
        return "sentence-transformers"
    return "disabled"


@lru_cache(maxsize=2)
def _load_embedder(provider: str, model_name: str, dimensions: int) -> Embedder | None:
    try:
        if provider == "hashing":
            return HashingEmbedder(dimensions)
        if provider == "fastembed":
            return FastEmbedEmbedder(model_name)
        if provider == "sentence-transformers":
            return SentenceTransformerEmbedder(model_name)
    except Exception:
        # Loading a model can fail offline or on unsupported hardware. The
        # caller falls back to BM25 and reports that mode explicitly.
        return None
    return None


def get_embedder(settings: Settings) -> Embedder | None:
    mode = embedding_mode(settings)
    if mode == "disabled":
        return None
    return _load_embedder(mode, settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSIONS)


def clear_embedder_cache() -> None:
    _load_embedder.cache_clear()
