from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import FakeLLMClient


def _r(rank: int, title: str = "t") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department="hr",
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text-{rank}",
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_answer_and_cited_chunk_ids():
    chunks = [_r(1, "A"), _r(2, "B"), _r(3, "C")]
    fake = FakeLLMClient(text_responses=["Answer references [1] and [3]."])
    out = await generate_answer(query="what?", chunks=chunks, conflicts=[], llm=fake)
    assert "[1]" in out.text and "[3]" in out.text
    assert out.cited_chunk_ids == [chunks[0].chunk_id, chunks[2].chunk_id]


@pytest.mark.asyncio
async def test_drops_out_of_range_markers():
    chunks = [_r(1, "A"), _r(2, "B")]
    fake = FakeLLMClient(text_responses=["Cited [1] and bogus [99]."])
    out = await generate_answer(query="q", chunks=chunks, conflicts=[], llm=fake)
    assert out.cited_chunk_ids == [chunks[0].chunk_id]


@pytest.mark.asyncio
async def test_assigns_conflict_markers_from_chunk_order():
    chunks = [_r(1, "A"), _r(2, "B")]
    # Pre-judge phase emits marker=0; generate_answer must re-assign markers
    raw = Conflict(
        subject="dress code",
        position_a=Position(marker=0, chunk_id=chunks[0].chunk_id, text="A says"),
        position_b=Position(marker=0, chunk_id=chunks[1].chunk_id, text="B says"),
    )
    fake = FakeLLMClient(text_responses=["Discussed [1] vs [2]."])
    out = await generate_answer(query="q", chunks=chunks, conflicts=[raw], llm=fake)
    assert out.conflicts[0].position_a.marker == 1
    assert out.conflicts[0].position_b.marker == 2


@pytest.mark.asyncio
async def test_empty_chunks_does_not_call_llm():
    fake = FakeLLMClient(text_responses=[])
    out = await generate_answer(query="q", chunks=[], conflicts=[], llm=fake)
    assert out.text == "I cannot answer this question with the available context."
    assert out.cited_chunk_ids == []
    assert out.conflicts == []
    assert fake.calls_text == []
