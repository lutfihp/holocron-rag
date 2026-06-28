from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation.citations import parse_citation_markers
from app.services.answer_generation.llm_client import LLMClient
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    render_context_block,
    render_conflicts_block,
)


@dataclass(frozen=True)
class AnswerWithCitations:
    text: str
    cited_chunk_ids: list[uuid.UUID]
    conflicts: list[Conflict]


_FALLBACK_ANSWER = "I cannot answer this question with the available context."


def _assign_conflict_markers(
    conflicts: list[Conflict], chunks: list[RetrievalResult]
) -> list[Conflict]:
    """Re-emit Conflicts with position markers set to the 1-based index of each
    chunk in the final citation list."""
    by_id_idx = {c.chunk_id: i + 1 for i, c in enumerate(chunks)}
    out: list[Conflict] = []
    for c in conflicts:
        m_a = by_id_idx.get(c.position_a.chunk_id, 0)
        m_b = by_id_idx.get(c.position_b.chunk_id, 0)
        out.append(
            Conflict(
                subject=c.subject,
                position_a=Position(marker=m_a, chunk_id=c.position_a.chunk_id, text=c.position_a.text),
                position_b=Position(marker=m_b, chunk_id=c.position_b.chunk_id, text=c.position_b.text),
            )
        )
    return out


async def generate_answer(
    *,
    query: str,
    chunks: list[RetrievalResult],
    conflicts: list[Conflict],
    llm: LLMClient,
) -> AnswerWithCitations:
    if not chunks:
        return AnswerWithCitations(text=_FALLBACK_ANSWER, cited_chunk_ids=[], conflicts=[])

    conflicts_with_markers = _assign_conflict_markers(conflicts, chunks)
    prompt = ANSWER_TEMPLATE_STR.format(
        context_str=render_context_block(chunks),
        conflicts_str=render_conflicts_block(conflicts_with_markers) or "(none)",
        query_str=query,
    )
    text = await llm.complete_text(prompt)
    cited_indices = parse_citation_markers(text, total_chunks=len(chunks))
    cited_chunk_ids = [chunks[i - 1].chunk_id for i in cited_indices]
    return AnswerWithCitations(
        text=text, cited_chunk_ids=cited_chunk_ids, conflicts=conflicts_with_markers
    )
