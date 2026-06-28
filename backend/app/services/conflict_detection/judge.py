from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, ConflictPair, Position
from app.services.answer_generation.llm_client import LLMClient, LLMUnavailable
from app.services.conflict_detection.prompts import render_judge_prompt

log = structlog.get_logger(__name__)

# Module-global cache: canonical pair key -> Conflict | None.
# functools.lru_cache doesn't fit async; we hand-roll a simple bounded dict.
_CACHE_CAPACITY = 256
_cache: "dict[tuple[uuid.UUID, uuid.UUID], Conflict | None]" = {}
_cache_order: list[tuple[uuid.UUID, uuid.UUID]] = []


def _judge_cache_clear() -> None:
    _cache.clear()
    _cache_order.clear()


def _cache_get(key: tuple[uuid.UUID, uuid.UUID]) -> tuple[bool, Conflict | None]:
    if key in _cache:
        return True, _cache[key]
    return False, None


def _cache_put(key: tuple[uuid.UUID, uuid.UUID], value: Conflict | None) -> None:
    if key in _cache:
        return
    _cache[key] = value
    _cache_order.append(key)
    while len(_cache_order) > _CACHE_CAPACITY:
        oldest = _cache_order.pop(0)
        _cache.pop(oldest, None)


def _build_conflict(payload: dict[str, Any], chunk_a: RetrievalResult, chunk_b: RetrievalResult) -> Conflict | None:
    if not payload.get("conflict"):
        return None
    return Conflict(
        subject=str(payload.get("subject", "")).strip() or "Unspecified",
        position_a=Position(marker=0, chunk_id=chunk_a.chunk_id, text=str(payload.get("position_a", "")).strip()),
        position_b=Position(marker=0, chunk_id=chunk_b.chunk_id, text=str(payload.get("position_b", "")).strip()),
    )


async def judge_pair(
    *,
    pair: ConflictPair,
    chunk_a: RetrievalResult,
    chunk_b: RetrievalResult,
    llm: LLMClient,
) -> Conflict | None:
    key = pair.canonical_key()
    hit, cached = _cache_get(key)
    if hit:
        return cached

    prompt = render_judge_prompt(
        a_title=chunk_a.document_title, a_date=chunk_a.effective_date.isoformat(),
        a_dept=chunk_a.department, a_text=chunk_a.snippet,
        b_title=chunk_b.document_title, b_date=chunk_b.effective_date.isoformat(),
        b_dept=chunk_b.department, b_text=chunk_b.snippet,
    )
    try:
        payload = await llm.complete_json(prompt)
    except LLMUnavailable as e:
        log.warning("judge LLM unavailable", pair=str(key), error=str(e))
        # Do not cache transient failures
        return None

    conflict = _build_conflict(payload, chunk_a, chunk_b)
    _cache_put(key, conflict)
    return conflict
