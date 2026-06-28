"""Pure scoring functions for the eval harness.

Three deterministic axes (retrieval, refusal, conflict). The fourth axis —
citation accuracy — needs an LLM call and lives in `runner.py`.
"""
from __future__ import annotations

from typing import Sequence


def score_retrieval_hit_rate(
    expected_lineages: Sequence[str], retrieved_lineages: Sequence[str]
) -> float:
    """Fraction of expected lineages that appeared in retrieved top-k.

    Empty `expected_lineages` is treated as "no expectation" → 1.0 (the
    refusal-category rows leave the list empty).
    """
    if not expected_lineages:
        return 1.0
    retrieved_set = set(retrieved_lineages)
    hits = sum(1 for l in expected_lineages if l in retrieved_set)
    return hits / len(expected_lineages)


def score_refusal_correctness(
    *,
    expected: bool,
    got: bool,
    withheld_count: int,
    min_withheld: int | None,
) -> float:
    """Binary correctness with optional withheld-count floor."""
    if expected != got:
        return 0.0
    if not expected:
        return 1.0  # both False — correctly answered, no over-refusal
    if min_withheld is not None and withheld_count < min_withheld:
        return 0.0
    return 1.0


def score_conflict_surfacing(
    conflicts: Sequence[dict], expected_keywords: Sequence[str]
) -> float:
    """1.0 if at least one returned conflict's `subject` substring-matches a
    keyword. Empty `expected_keywords` is "no expectation" → 1.0 regardless."""
    if not expected_keywords:
        return 1.0
    for c in conflicts:
        subject = (c.get("subject") or "").lower()
        if any(kw.lower() in subject for kw in expected_keywords):
            return 1.0
    return 0.0
