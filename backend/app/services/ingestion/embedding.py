from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

EMBEDDING_DIM = 768


class EmbeddingProvider(Protocol):
    """Protocol every embedder implements. Tests inject the Fake; production uses BGE."""

    def embed_one(self, text: str) -> np.ndarray: ...

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]: ...


class FakeEmbeddingProvider:
    """Deterministic hash-based embeddings for tests.

    Bag-of-overlapping-trigrams + words hashed into bucket positions. Two texts
    that share many tokens land closer in vector space than two that don't.
    Not a real semantic embedding — but enough to make 'similar query retrieves
    similar chunk' behavior deterministic for retrieval tests.
    """

    def embed_one(self, text: str) -> np.ndarray:
        v = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        normalized = text.lower().strip()
        if not normalized:
            return v
        for token in normalized.split():
            idx = (
                int(hashlib.blake2b(token.encode("utf-8"), digest_size=4).hexdigest(), 16)
                % EMBEDDING_DIM
            )
            v[idx] += 1.0
        for i in range(len(normalized) - 2):
            tri = normalized[i : i + 3]
            idx = (
                int(hashlib.blake2b(tri.encode("utf-8"), digest_size=4).hexdigest(), 16)
                % EMBEDDING_DIM
            )
            v[idx] += 0.5
        norm = float(np.linalg.norm(v))
        if norm > 0:
            v /= norm
        return v

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed_one(t) for t in texts]


class BgeEmbeddingProvider:
    """Local BAAI/bge-base-en-v1.5 via sentence-transformers (768-dim).

    First instantiation downloads ~440 MB. Subsequent runs are cached in
    HF_HOME (default ~/.cache/huggingface)."""

    _MODEL_NAME = "BAAI/bge-base-en-v1.5"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import; defer

        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed_one(self, text: str) -> np.ndarray:
        v = self._model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(v, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        arr = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, batch_size=32
        )
        return [np.asarray(row, dtype=np.float32) for row in arr]
