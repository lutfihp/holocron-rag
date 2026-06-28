from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.services.answer_generation.llm_client import FakeLLMClient
from app.services.conflict_detection import detect_conflicts


def _r(*, dept: str, lineage: uuid.UUID, rank: int, title: str = "t") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department=dept,
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text {rank}",
        score=0.0,
        rank=rank,
        lineage_id=lineage,
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_empty_when_no_pairs():
    a = _r(dept="hr", lineage=uuid.uuid4(), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), rank=2)
    conflicts = await detect_conflicts(results=[a, b], llm=FakeLLMClient())
    assert conflicts == []


@pytest.mark.asyncio
async def test_detects_lineage_pair():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, rank=1, title="Handbook 2019")
    b = _r(dept="hr", lineage=L, rank=2, title="Supplement 2023")
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "insignia",
        "position_a": "no insignia off-base",
        "position_b": "may retain unit insignia",
    }])
    conflicts = await detect_conflicts(results=[a, b], llm=fake)
    assert len(conflicts) == 1
    assert conflicts[0].subject == "insignia"


@pytest.mark.asyncio
async def test_filters_out_no_conflict_judgments():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, rank=1)
    b = _r(dept="hr", lineage=L, rank=2)
    fake = FakeLLMClient(json_responses=[{
        "conflict": False, "subject": "", "position_a": "", "position_b": "",
    }])
    conflicts = await detect_conflicts(results=[a, b], llm=fake)
    assert conflicts == []
