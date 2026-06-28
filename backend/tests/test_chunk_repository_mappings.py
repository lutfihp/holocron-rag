"""Phase D: smoke-check that .mappings() reads keep the ChunkHit contract.

The real safety net is the existing chunk/retrieval test suite passing after
the positional-row → named-column migration. This file just locks down the
ChunkHit field set so a future column rename surfaces here loudly.
"""
from __future__ import annotations

from app.repositories.chunk_repository import ChunkHit


def test_chunk_hit_has_all_columns_needed_downstream():
    fields = set(ChunkHit.__dataclass_fields__)
    assert {
        "chunk_id",
        "document_id",
        "document_title",
        "classification",
        "department",
        "effective_date",
        "snippet",
        "score",
        "rank",
        "lineage_id",
        "entities",
    } <= fields
