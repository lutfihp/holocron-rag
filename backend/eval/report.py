"""Markdown + JSON scorecard writer for the eval harness."""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from eval.runner import QuestionResult


def _aggregate(results: Iterable[QuestionResult]) -> dict:
    results = list(results)
    by_cat: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    out: dict = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "categories": {},
    }
    for cat, rs in by_cat.items():
        out["categories"][cat] = {
            "n": len(rs),
            "passed": sum(1 for r in rs if r.passed),
        }
    return out


def diff_runs(
    curr_results: list[QuestionResult], prev_results: list[QuestionResult]
) -> tuple[list[str], list[str]]:
    """Returns (regressions, improvements) by question id."""
    prev_by_id = {r.id: r for r in prev_results}
    regressions: list[str] = []
    improvements: list[str] = []
    for c in curr_results:
        p = prev_by_id.get(c.id)
        if p is None:
            continue
        if p.passed and not c.passed:
            regressions.append(c.id)
        elif not p.passed and c.passed:
            improvements.append(c.id)
    return regressions, improvements


def _load_prev(reports_dir: Path, *, exclude: str) -> list[QuestionResult] | None:
    candidates = sorted(p for p in reports_dir.glob("*.json") if p.stem != exclude)
    if not candidates:
        return None
    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    return [QuestionResult(**q) for q in payload["questions"]]


def write_report(
    results: list[QuestionResult],
    *,
    md_path: Path,
    json_path: Path,
    reports_dir: Path,
) -> None:
    agg = _aggregate(results)

    payload = {
        "date": dt.date.today().isoformat(),
        "questions": [asdict(r) for r in results],
        "aggregate": agg,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    prev_results = _load_prev(reports_dir, exclude=md_path.stem)
    regressions, improvements = (
        diff_runs(results, prev_results) if prev_results else ([], [])
    )

    lines = [f"# HOLOCRON Eval — {payload['date']}", ""]
    lines.append(f"**Total: {agg['passed']}/{agg['total']} passed**\n")
    lines.append("| Category | N | Passed |")
    lines.append("|---|---|---|")
    for cat, c in sorted(agg["categories"].items()):
        lines.append(f"| {cat} | {c['n']} | {c['passed']} |")
    lines.append("")
    if regressions:
        lines.append("## Regressions")
        for qid in regressions:
            lines.append(f"- `{qid}`")
        lines.append("")
    if improvements:
        lines.append("## Improvements")
        for qid in improvements:
            lines.append(f"- `{qid}`")
        lines.append("")
    lines.append("## Per-question")
    lines.append("| ID | Category | Pass | Scores | Notes |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        scores = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(r.scores.items()))
        check = "✓" if r.passed else "✗"
        notes = r.notes.replace("|", "\\|") if r.notes else ""
        lines.append(f"| `{r.id}` | {r.category} | {check} | {scores} | {notes} |")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
