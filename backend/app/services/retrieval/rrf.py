from __future__ import annotations

from typing import Hashable, Sequence, TypeVar

T = TypeVar("T", bound=Hashable)


def rrf_fuse(
    list_a: Sequence[tuple[T, int]],
    list_b: Sequence[tuple[T, int]],
    *,
    k: int = 60,
) -> list[tuple[T, float]]:
    """Reciprocal Rank Fusion.

    Each input is `[(item_id, rank)]` where rank starts at 1. Score per item =
    sum over lists of `1 / (k + rank)`. Returns items sorted by descending score.
    """
    scores: dict[T, float] = {}
    for ranked in (list_a, list_b):
        for item_id, rank in ranked:
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
