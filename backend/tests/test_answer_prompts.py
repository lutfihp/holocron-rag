from __future__ import annotations

import datetime as dt
import uuid

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    REFINE_TEMPLATE_STR,
    render_context_block,
    render_conflicts_block,
)


def _r(rank: int, title: str, dept: str, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department=dept,
        effective_date=dt.date(2023, 1, 1),
        snippet=text,
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


def test_context_block_numbers_chunks_starting_at_one():
    chunks = [_r(1, "A", "hr", "text-a"), _r(2, "B", "security", "text-b")]
    out = render_context_block(chunks)
    assert "[1]" in out and "[2]" in out
    assert "text-a" in out and "text-b" in out
    assert "doc: \"A\"" in out and "doc: \"B\"" in out


def test_conflicts_block_uses_provided_markers():
    chunks = [_r(1, "A", "hr", "ta"), _r(2, "B", "hr", "tb")]
    c = Conflict(
        subject="dress code",
        position_a=Position(marker=1, chunk_id=chunks[0].chunk_id, text="no insignia"),
        position_b=Position(marker=2, chunk_id=chunks[1].chunk_id, text="may retain"),
    )
    out = render_conflicts_block([c])
    assert "Subject: dress code" in out
    assert "[1] states: no insignia" in out
    assert "[2] states: may retain" in out


def test_conflicts_block_empty_when_no_conflicts():
    assert render_conflicts_block([]) == ""


def test_answer_template_contains_required_markers():
    # Sanity: template surfaces query_str + context_str + conflicts_str placeholders
    assert "{context_str}" in ANSWER_TEMPLATE_STR
    assert "{query_str}" in ANSWER_TEMPLATE_STR
    assert "{conflicts_str}" in ANSWER_TEMPLATE_STR
    assert "[1]" in ANSWER_TEMPLATE_STR  # example shape


def test_refine_template_preserves_markers_instruction():
    assert "{query_str}" in REFINE_TEMPLATE_STR
    assert "preserve" in REFINE_TEMPLATE_STR.lower() or "keep" in REFINE_TEMPLATE_STR.lower()
