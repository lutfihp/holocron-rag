from __future__ import annotations

from itertools import combinations

from app.domain.chunk import RetrievalResult
from app.domain.conflict import ConflictPair

MAX_PAIRS_PER_QUERY = 4
SAME_DEPT_ENTITY_THRESHOLD = 2
CROSS_DEPT_ENTITY_THRESHOLD = 3


def _is_candidate(a: RetrievalResult, b: RetrievalResult) -> bool:
    if a.chunk_id == b.chunk_id:
        return False
    if a.lineage_id == b.lineage_id:
        return True
    overlap = len(set(a.entities) & set(b.entities))
    if a.department == b.department:
        return overlap >= SAME_DEPT_ENTITY_THRESHOLD
    return overlap >= CROSS_DEPT_ENTITY_THRESHOLD


def build_candidate_pairs(results: list[RetrievalResult]) -> list[ConflictPair]:
    candidates: dict[tuple, ConflictPair] = {}
    for a, b in combinations(results, 2):
        if not _is_candidate(a, b):
            continue
        pair = ConflictPair(
            chunk_a_id=a.chunk_id,
            chunk_b_id=b.chunk_id,
            a_rank=a.rank,
            b_rank=b.rank,
        )
        candidates.setdefault(pair.canonical_key(), pair)
    ranked = sorted(candidates.values(), key=lambda p: p.rank_sum())
    return ranked[:MAX_PAIRS_PER_QUERY]
