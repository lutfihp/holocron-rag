from __future__ import annotations

from functools import lru_cache

from app.services.ingestion.embedding import BgeEmbeddingProvider, EmbeddingProvider


@lru_cache
def get_default_embedder() -> EmbeddingProvider:
    """Cached singleton — the BGE model loads once per process."""
    return BgeEmbeddingProvider()
