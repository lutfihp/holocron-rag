from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.domain.conflict import ConflictPair
from app.services.answer_generation.llm_client import FakeLLMClient
from app.services.conflict_detection.judge import judge_pair


def _r(rank: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=f"Doc{rank}",
        classification="public",
        department="hr",
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text {rank}",
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_conflict_when_llm_says_so():
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True,
        "subject": "audit cadence",
        "position_a": "weekly",
        "position_b": "monthly",
    }])
    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert result is not None
    assert result.subject == "audit cadence"
    assert result.position_a.text == "weekly"
    assert result.position_b.text == "monthly"


@pytest.mark.asyncio
async def test_returns_none_when_llm_says_no_conflict():
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": False, "subject": "", "position_a": "", "position_b": "",
    }])
    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_skips_llm_for_same_pair():
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "s", "position_a": "x", "position_b": "y",
    }])
    out1 = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    out2 = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert out1 is not None and out2 is not None
    assert len(fake.calls_json) == 1


@pytest.mark.asyncio
async def test_cache_key_is_orderless():
    a, b = _r(1), _r(2)
    pair_ab = ConflictPair(a.chunk_id, b.chunk_id, 1, 2)
    pair_ba = ConflictPair(b.chunk_id, a.chunk_id, 2, 1)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "s", "position_a": "x", "position_b": "y",
    }])
    await judge_pair(pair=pair_ab, chunk_a=a, chunk_b=b, llm=fake)
    await judge_pair(pair=pair_ba, chunk_a=b, chunk_b=a, llm=fake)
    assert len(fake.calls_json) == 1


@pytest.mark.asyncio
async def test_returns_none_on_llm_unavailable():
    from app.services.answer_generation.llm_client import LLMUnavailable

    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, 1, 2)

    class _RaisingLLM:
        async def complete_json(self, _p: str) -> dict:
            raise LLMUnavailable("boom")
        async def complete_text(self, _p: str) -> str:
            raise LLMUnavailable("boom")

    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=_RaisingLLM())
    assert result is None
