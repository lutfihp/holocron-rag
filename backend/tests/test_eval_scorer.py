from __future__ import annotations

from eval.scorer import (
    score_conflict_surfacing,
    score_refusal_correctness,
    score_retrieval_hit_rate,
)


# ---- retrieval hit-rate ----


def test_retrieval_all_expected_present_returns_one():
    assert score_retrieval_hit_rate(
        ["employee-handbook", "management-supplement"],
        ["employee-handbook", "management-supplement", "other"],
    ) == 1.0


def test_retrieval_half_present_returns_half():
    assert score_retrieval_hit_rate(["a", "b"], ["a", "x"]) == 0.5


def test_retrieval_none_present_returns_zero():
    assert score_retrieval_hit_rate(["a"], []) == 0.0


def test_retrieval_empty_expected_treated_as_pass():
    assert score_retrieval_hit_rate([], ["anything"]) == 1.0


# ---- refusal correctness ----


def test_refusal_expected_and_got_and_min_met():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=3, min_withheld=1) == 1.0


def test_refusal_expected_and_got_no_min():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=0, min_withheld=None) == 1.0


def test_refusal_expected_but_min_not_met_fails():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=1, min_withheld=3) == 0.0


def test_refusal_unexpected_but_got_one():
    assert score_refusal_correctness(expected=False, got=True, withheld_count=0, min_withheld=None) == 0.0


def test_refusal_expected_but_missing():
    assert score_refusal_correctness(expected=True, got=False, withheld_count=0, min_withheld=None) == 0.0


def test_refusal_neither_expected_nor_got():
    assert score_refusal_correctness(expected=False, got=False, withheld_count=0, min_withheld=None) == 1.0


# ---- conflict surfacing ----


def test_conflict_keyword_substring_match():
    conflicts = [{"subject": "off-duty insignia and accessory standards"}]
    assert score_conflict_surfacing(conflicts, ["insignia", "off-duty"]) == 1.0


def test_conflict_no_match():
    conflicts = [{"subject": "completely unrelated"}]
    assert score_conflict_surfacing(conflicts, ["insignia"]) == 0.0


def test_conflict_no_keywords_pass():
    assert score_conflict_surfacing([], []) == 1.0


def test_conflict_expected_but_no_conflicts_returned_fails():
    assert score_conflict_surfacing([], ["insignia"]) == 0.0
