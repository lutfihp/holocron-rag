"""Eval orchestrator: load YAML → run two passes per question → score → report.

Public entry: `python -m eval.runner` (run from `backend/`) or `make eval`.

Architecture:
  - HolocronApiClient calls /retrieval/search and /chat/ask via httpx
  - The same Groq client used by /chat/ask judges citation accuracy
  - eval.scorer functions compute deterministic axes
  - run_single_question is the unit of work; pure I/O against the api client
  - run_all collects QuestionResult dataclasses for eval.report
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Protocol

import httpx
import yaml

from eval.prompts import CITATION_JUDGE_PROMPT
from eval.scorer import (
    score_conflict_surfacing,
    score_refusal_correctness,
    score_retrieval_hit_rate,
)


# Mirror app.services.ingestion.pipeline._LINEAGE_NS so slug→UUID matches the
# values the API returns.
_LINEAGE_NS = uuid.UUID("e7b3a2d4-1c5e-4f8a-9b6d-7a3c0f1e2a4b")


def lineage_uuid(slug: str) -> uuid.UUID:
    return uuid.uuid5(_LINEAGE_NS, slug)


# ---- Data shapes ----

@dataclass
class EvalQuestion:
    id: str
    category: str            # lookup | refusal | conflict | cross_department
    as_user: str
    question: str
    expected: dict[str, Any]


@dataclass
class RetrievalResponse:
    retrieved_lineages: list[str]   # slugs
    refused: bool
    withheld_count: int


@dataclass
class ChatResponse:
    retrieved_lineages: list[str]
    refused: bool
    withheld_count: int
    conflicts: list[dict]
    answer: str
    cited_snippets: list[dict]


@dataclass
class QuestionResult:
    id: str
    category: str
    scores: dict[str, float] = field(default_factory=dict)
    passed: bool = False
    notes: str = ""


# ---- API client protocol (for testability) ----

class _ApiProto(Protocol):
    async def search(self, *, question: str, as_user: str) -> RetrievalResponse: ...
    async def chat(self, *, question: str, as_user: str) -> ChatResponse: ...
    async def judge_citation(
        self, *, question: str, answer: str, snippets: list[dict]
    ) -> float: ...


# ---- Slug reverse lookup ----

def _build_slug_index() -> dict[str, str]:
    """Pre-compute uuid-str -> slug for every lineage in the corpus."""
    from pathlib import Path
    import re
    corpus_root = Path(__file__).resolve().parents[2] / "corpus"
    slugs: set[str] = set()
    if corpus_root.exists():
        for md in corpus_root.rglob("*.md"):
            for line in md.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^lineage_id:\s*(\S+)\s*$", line)
                if m:
                    slugs.add(m.group(1))
                    break
    return {str(lineage_uuid(s)): s for s in slugs}


_SLUG_INDEX = _build_slug_index()


def _uuid_to_slug(u: str) -> str:
    """Return the corpus slug for a lineage UUID string, or the UUID if unknown."""
    return _SLUG_INDEX.get(u, u)


# ---- HTTP client ----

class HolocronApiClient:
    """Logs in once per username, caches cookies, calls the two endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url
        self._cookies_by_user: dict[str, dict[str, str]] = {}
        self._tenant_id: str | None = None
        self._client = httpx.AsyncClient(timeout=120.0)

    async def _resolve_tenant_id(self) -> str:
        if self._tenant_id:
            return self._tenant_id
        # Read from env (preferred — set in conftest of the dev quickstart) or fall
        # back to a friendly error. We don't have a public discovery endpoint.
        tid = os.getenv("HOLOCRON_TENANT_ID")
        if not tid:
            raise RuntimeError(
                "HOLOCRON_TENANT_ID env var is required to run eval. "
                "Get it from `python scripts/seed_users.py` or check the value in "
                "frontend/.env.local NEXT_PUBLIC_DEFAULT_TENANT_ID."
            )
        self._tenant_id = tid
        return tid

    async def _login(self, username: str) -> dict[str, str]:
        if username in self._cookies_by_user:
            return self._cookies_by_user[username]
        tenant_id = await self._resolve_tenant_id()
        resp = await self._client.post(
            f"{self.base_url}/auth/login",
            json={
                "tenant_id": tenant_id,
                "username": username,
                "password": "imperial-march",
            },
        )
        resp.raise_for_status()
        cookies = {k: v for k, v in resp.cookies.items()}
        self._cookies_by_user[username] = cookies
        return cookies

    async def search(self, *, question: str, as_user: str) -> RetrievalResponse:
        cookies = await self._login(as_user)
        resp = await self._client.post(
            f"{self.base_url}/retrieval/search",
            json={"query": question, "top_k": 6},
            cookies=cookies,
        )
        resp.raise_for_status()
        body = resp.json()
        retrieved_lineages = [_uuid_to_slug(c["lineage_id"]) for c in body.get("results", [])]
        refusal = body.get("refusal")
        return RetrievalResponse(
            retrieved_lineages=retrieved_lineages,
            refused=bool(refusal),
            withheld_count=(refusal or {}).get("withheld_count", 0),
        )

    async def chat(self, *, question: str, as_user: str) -> ChatResponse:
        cookies = await self._login(as_user)
        resp = await self._client.post(
            f"{self.base_url}/chat/ask",
            json={"query": question, "top_k": 6},
            cookies=cookies,
        )
        resp.raise_for_status()
        body = resp.json()
        citations = body.get("citations", [])
        retrieved_lineages = [_uuid_to_slug(c["lineage_id"]) for c in citations]
        refusal = body.get("refusal")
        return ChatResponse(
            retrieved_lineages=retrieved_lineages,
            refused=bool(refusal),
            withheld_count=(refusal or {}).get("withheld_count", 0),
            conflicts=body.get("conflicts", []),
            answer=body.get("answer", {}).get("text", ""),
            cited_snippets=[
                {"marker": c["marker"], "snippet": c["snippet"]} for c in citations
            ],
        )

    async def judge_citation(
        self, *, question: str, answer: str, snippets: list[dict]
    ) -> float:
        if not snippets:
            return 1.0
        cache_key = _cache_key(question, answer, snippets)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        from app.services.answer_generation.llm_client import get_default_llm
        llm = get_default_llm()
        snippets_block = "\n".join(
            f"[{s['marker']}] {s['snippet']}" for s in snippets
        )
        prompt = CITATION_JUDGE_PROMPT.format(
            question=question, answer=answer, snippets=snippets_block
        )
        try:
            result = await llm.complete_json(prompt)
            score = float(result.get("score", 0.0))
        except Exception as e:  # noqa: BLE001
            print(f"  (judge error: {e})", file=sys.stderr)
            score = 0.0
        _cache_put(cache_key, score)
        return score

    async def close(self) -> None:
        await self._client.aclose()


# ---- Judge response cache (eval-only, gitignored) ----

_CACHE_DIR = Path(__file__).parent / ".cache"


def _cache_key(question: str, answer: str, snippets: list[dict]) -> str:
    import hashlib
    payload = json.dumps(
        {"q": question, "a": answer, "s": snippets}, sort_keys=True
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _cache_get(key: str) -> float | None:
    f = _CACHE_DIR / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))["score"]
    return None


def _cache_put(key: str, score: float) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"{key}.json").write_text(
        json.dumps({"score": score}), encoding="utf-8"
    )


# ---- Per-question execution ----

async def run_single_question(q: EvalQuestion, api: _ApiProto) -> QuestionResult:
    result = QuestionResult(id=q.id, category=q.category)
    expected = q.expected

    if q.category == "refusal":
        # Only full-stack pass; no retrieval expectation.
        chat = await api.chat(question=q.question, as_user=q.as_user)
        result.scores["refusal"] = score_refusal_correctness(
            expected=bool(expected.get("must_refuse")),
            got=chat.refused,
            withheld_count=chat.withheld_count,
            min_withheld=expected.get("refusal_min_withheld"),
        )
    else:
        retrieval = await api.search(question=q.question, as_user=q.as_user)
        chat = await api.chat(question=q.question, as_user=q.as_user)
        result.scores["retrieval"] = score_retrieval_hit_rate(
            expected.get("must_cite_lineages", []),
            retrieval.retrieved_lineages,
        )
        result.scores["refusal"] = score_refusal_correctness(
            expected=bool(expected.get("must_refuse")),
            got=chat.refused,
            withheld_count=chat.withheld_count,
            min_withheld=expected.get("refusal_min_withheld"),
        )
        if q.category in ("conflict", "cross_department"):
            result.scores["conflict"] = score_conflict_surfacing(
                chat.conflicts, expected.get("conflict_subject_keywords", []),
            )
        result.scores["citation"] = await api.judge_citation(
            question=q.question, answer=chat.answer, snippets=chat.cited_snippets,
        )

    result.passed = all(s >= 0.5 for s in result.scores.values())
    return result


# ---- Top-level orchestration ----

def load_golden_set(path: Path) -> list[EvalQuestion]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [EvalQuestion(**entry) for entry in raw]


async def run_all() -> list[QuestionResult]:
    here = Path(__file__).parent
    questions = load_golden_set(here / "golden_set.yaml")
    api = HolocronApiClient(
        base_url=os.getenv("HOLOCRON_BASE_URL", "http://localhost:8000"),
    )
    try:
        results: list[QuestionResult] = []
        for q in questions:
            print(
                f"  → {q.id} ({q.category}, as {q.as_user})",
                file=sys.stderr,
            )
            try:
                results.append(await run_single_question(q, api))
            except Exception as e:  # noqa: BLE001
                r = QuestionResult(id=q.id, category=q.category)
                r.notes = f"runner error: {e}"
                results.append(r)
        return results
    finally:
        await api.close()


def main() -> None:
    from eval.report import write_report
    results = asyncio.run(run_all())
    here = Path(__file__).parent
    today = dt.date.today().isoformat()
    reports_dir = here / "reports"
    md_path = reports_dir / f"{today}.md"
    json_path = reports_dir / f"{today}.json"
    write_report(results, md_path=md_path, json_path=json_path, reports_dir=reports_dir)
    passed = sum(1 for r in results if r.passed)
    print(f"\n{passed}/{len(results)} questions passed", file=sys.stderr)


if __name__ == "__main__":
    main()
