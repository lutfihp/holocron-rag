from __future__ import annotations

import json
from pathlib import Path

from eval.report import diff_runs, write_report
from eval.runner import QuestionResult


def _r(qid: str, category: str, scores: dict, passed: bool) -> QuestionResult:
    out = QuestionResult(id=qid, category=category)
    out.scores = scores
    out.passed = passed
    return out


def test_write_report_creates_markdown_and_json(tmp_path: Path):
    results = [
        _r("q1", "lookup", {"retrieval": 1.0, "refusal": 1.0, "citation": 0.9}, True),
        _r("q2", "refusal", {"refusal": 1.0}, True),
        _r(
            "q3",
            "conflict",
            {"retrieval": 1.0, "refusal": 1.0, "citation": 0.8, "conflict": 0.0},
            False,
        ),
    ]
    md_path = tmp_path / "x.md"
    json_path = tmp_path / "x.json"
    write_report(results, md_path=md_path, json_path=json_path, reports_dir=tmp_path)

    assert md_path.exists()
    assert json_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload["questions"]) == 3
    assert payload["aggregate"]["passed"] == 2
    md = md_path.read_text(encoding="utf-8")
    assert "lookup" in md and "refusal" in md and "conflict" in md


def test_diff_runs_identifies_regressions():
    prev = [_r("q1", "lookup", {"retrieval": 1.0}, True)]
    curr = [_r("q1", "lookup", {"retrieval": 0.0}, False)]
    regs, imps = diff_runs(curr_results=curr, prev_results=prev)
    assert regs == ["q1"]
    assert imps == []


def test_diff_runs_identifies_improvements():
    prev = [_r("q1", "lookup", {"retrieval": 0.0}, False)]
    curr = [_r("q1", "lookup", {"retrieval": 1.0}, True)]
    regs, imps = diff_runs(curr_results=curr, prev_results=prev)
    assert regs == []
    assert imps == ["q1"]


def test_diff_runs_ignores_unmatched_ids():
    prev = [_r("q1", "lookup", {"retrieval": 1.0}, True)]
    curr = [_r("q2", "lookup", {"retrieval": 1.0}, True)]
    regs, imps = diff_runs(curr_results=curr, prev_results=prev)
    assert regs == [] and imps == []
