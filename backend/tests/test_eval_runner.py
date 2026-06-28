from __future__ import annotations

import pytest

from eval.runner import (
    ChatResponse,
    EvalQuestion,
    RetrievalResponse,
    run_single_question,
)


class _FakeApi:
    def __init__(self) -> None:
        self.retrieval = RetrievalResponse(
            retrieved_lineages=["employee-handbook"],
            refused=False,
            withheld_count=0,
        )
        self.chat_resp = ChatResponse(
            retrieved_lineages=["employee-handbook"],
            refused=False,
            withheld_count=0,
            conflicts=[],
            answer="HR runs the office [1].",
            cited_snippets=[{"marker": 1, "snippet": "HR runs the office."}],
        )
        self.citation_score = 1.0

    async def search(self, *, question: str, as_user: str) -> RetrievalResponse:
        return self.retrieval

    async def chat(self, *, question: str, as_user: str) -> ChatResponse:
        return self.chat_resp

    async def judge_citation(self, *, question, answer, snippets) -> float:
        return self.citation_score


@pytest.mark.asyncio
async def test_run_single_lookup_question_passes_all_axes():
    q = EvalQuestion(
        id="dress-code-1",
        category="lookup",
        as_user="employee.security",
        question="Who runs HR?",
        expected={
            "must_refuse": False,
            "must_cite_lineages": ["employee-handbook"],
        },
    )
    api = _FakeApi()
    result = await run_single_question(q, api)

    assert result.id == "dress-code-1"
    assert result.scores["retrieval"] == 1.0
    assert result.scores["refusal"] == 1.0
    assert result.scores["citation"] == 1.0
    assert result.passed


@pytest.mark.asyncio
async def test_run_single_refusal_skips_retrieval_axis():
    q = EvalQuestion(
        id="refusal-1",
        category="refusal",
        as_user="employee.security",
        question="What's the executive search protocol?",
        expected={"must_refuse": True, "refusal_min_withheld": 1},
    )
    api = _FakeApi()
    api.chat_resp = ChatResponse(
        retrieved_lineages=[],
        refused=True,
        withheld_count=2,
        conflicts=[],
        answer="",
        cited_snippets=[],
    )
    result = await run_single_question(q, api)

    assert result.scores["refusal"] == 1.0
    assert "retrieval" not in result.scores
    assert result.passed


@pytest.mark.asyncio
async def test_run_single_conflict_includes_conflict_axis():
    q = EvalQuestion(
        id="conflict-1",
        category="conflict",
        as_user="director.engineering",
        question="reactor coolant sequence?",
        expected={
            "must_refuse": False,
            "must_cite_lineages": ["reactor-manual"],
            "must_flag_conflict": True,
            "conflict_subject_keywords": ["shutdown", "sequence"],
        },
    )
    api = _FakeApi()
    api.retrieval = RetrievalResponse(
        retrieved_lineages=["reactor-manual"], refused=False, withheld_count=0
    )
    api.chat_resp = ChatResponse(
        retrieved_lineages=["reactor-manual"],
        refused=False,
        withheld_count=0,
        conflicts=[{"subject": "coolant shutdown sequence differs"}],
        answer="2019 says X; 2023 says Y [1][2].",
        cited_snippets=[{"marker": 1, "snippet": "X"}, {"marker": 2, "snippet": "Y"}],
    )
    result = await run_single_question(q, api)
    assert result.scores["conflict"] == 1.0
    assert result.passed


@pytest.mark.asyncio
async def test_run_single_records_failed_axis():
    q = EvalQuestion(
        id="fail-1",
        category="lookup",
        as_user="employee.security",
        question="?",
        expected={
            "must_refuse": False,
            "must_cite_lineages": ["nonexistent-lineage"],
        },
    )
    api = _FakeApi()
    result = await run_single_question(q, api)
    assert result.scores["retrieval"] == 0.0
    assert not result.passed
