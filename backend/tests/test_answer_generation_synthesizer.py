from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import FakeLLMClient


def _make_result(idx: int, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=f"Doc {idx}",
        classification="public",
        department="hr",
        effective_date=dt.date(2024, 1, 1),
        snippet=text,
        score=0.0,
        rank=idx,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


@pytest.mark.asyncio
async def test_generate_answer_uses_synthesizer_path():
    """End-to-end: CompactAndRefine.asynthesize through HolocronGroqLLM(Fake).

    Verifies the synthesizer fires the LLM, the scripted text propagates back,
    and citation markers are parsed against the chunk ordering.
    """
    chunks = [_make_result(1, "HR runs the office."), _make_result(2, "HR sets dress code.")]
    fake = FakeLLMClient(text_responses=["HR runs the office and sets dress code [1][2]."])

    result = await generate_answer(query="Who runs HR?", chunks=chunks, conflicts=[], llm=fake)

    assert "HR runs the office and sets dress code" in result.text
    assert set(result.cited_chunk_ids) == {chunks[0].chunk_id, chunks[1].chunk_id}
    assert fake.calls_text, "synthesizer should have made at least one LLM call"


@pytest.mark.asyncio
async def test_generate_answer_empty_chunks_does_not_invoke_synthesizer():
    fake = FakeLLMClient()  # no scripted responses; should never be called
    result = await generate_answer(query="anything", chunks=[], conflicts=[], llm=fake)
    assert "cannot answer" in result.text.lower()
    assert result.cited_chunk_ids == []
    assert fake.calls_text == []
