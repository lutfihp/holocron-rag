from __future__ import annotations

import asyncio

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict
from app.services.answer_generation.llm_client import LLMClient
from app.services.conflict_detection.judge import judge_pair
from app.services.conflict_detection.prefilter import build_candidate_pairs


async def detect_conflicts(
    *, results: list[RetrievalResult], llm: LLMClient
) -> list[Conflict]:
    pairs = build_candidate_pairs(results)
    if not pairs:
        return []
    by_id = {r.chunk_id: r for r in results}
    coros = [
        judge_pair(pair=p, chunk_a=by_id[p.chunk_a_id], chunk_b=by_id[p.chunk_b_id], llm=llm)
        for p in pairs
    ]
    judged = await asyncio.gather(*coros)
    return [c for c in judged if c is not None]
