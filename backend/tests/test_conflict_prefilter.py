from __future__ import annotations

import datetime as dt
import uuid

from app.domain.chunk import RetrievalResult
from app.services.conflict_detection.prefilter import (
    MAX_PAIRS_PER_QUERY,
    build_candidate_pairs,
)


def _r(
    *,
    dept: str,
    lineage: uuid.UUID,
    ents: tuple[str, ...],
    rank: int,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="t",
        classification="public",
        department=dept,
        effective_date=dt.date(2024, 1, 1),
        snippet="x",
        score=0.0,
        rank=rank,
        lineage_id=lineage,
        entities=ents,
    )


def test_lineage_pair_is_a_candidate():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, ents=(), rank=1)
    b = _r(dept="hr", lineage=L, ents=(), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1
    assert pairs[0].canonical_key() == tuple(sorted((a.chunk_id, b.chunk_id)))


def test_same_dept_two_overlapping_entities_is_a_candidate():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "cadence", "policy"), rank=1)
    b = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "cadence", "other"), rank=3)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1


def test_same_dept_one_overlapping_entity_is_not():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit",), rank=1)
    b = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "other"), rank=3)
    pairs = build_candidate_pairs([a, b])
    assert pairs == []


def test_cross_dept_three_overlapping_entities_is_a_candidate():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "incident", "review"), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), ents=("audit", "incident", "review"), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1


def test_cross_dept_two_overlapping_entities_is_not():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "incident"), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), ents=("audit", "incident"), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert pairs == []


def test_caps_to_max_pairs_per_query():
    L = uuid.uuid4()
    chunks = [_r(dept="hr", lineage=L, ents=(), rank=i + 1) for i in range(6)]
    # All same lineage -> C(6,2)=15 candidate pairs raw
    pairs = build_candidate_pairs(chunks)
    assert len(pairs) == MAX_PAIRS_PER_QUERY


def test_pairs_sorted_by_rank_sum_ascending():
    L = uuid.uuid4()
    c1 = _r(dept="hr", lineage=L, ents=(), rank=1)
    c2 = _r(dept="hr", lineage=L, ents=(), rank=2)
    c3 = _r(dept="hr", lineage=L, ents=(), rank=5)
    pairs = build_candidate_pairs([c1, c2, c3])
    assert pairs[0].rank_sum() <= pairs[1].rank_sum() <= pairs[2].rank_sum()


def test_pair_key_orderless_dedup():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, ents=(), rank=1)
    b = _r(dept="hr", lineage=L, ents=(), rank=2)
    pairs = build_candidate_pairs([a, b, b, a])  # synthetic dup input
    keys = {p.canonical_key() for p in pairs}
    assert len(keys) == len(pairs)
