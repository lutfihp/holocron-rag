from __future__ import annotations

import uuid
from dataclasses import dataclass

from llama_index.core import PromptTemplate
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.schema import NodeWithScore, TextNode

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation.citations import parse_citation_markers
from app.services.answer_generation.groq_llm_adapter import HolocronGroqLLM
from app.services.answer_generation.llm_client import LLMClient, LLMUnavailable
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    REFINE_TEMPLATE_STR,
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


def _escape_template_braces(s: str) -> str:
    """Double any `{` / `}` so a downstream PromptTemplate.format() does not
    try to interpret stray braces in pre-substituted content as placeholders."""
    return s.replace("{", "{{").replace("}", "}}")


def _render_one_chunk(idx: int, c: RetrievalResult) -> str:
    """One numbered chunk block — carries the `[N]` citation marker and the
    metadata header inline so the synthesizer's `{context_str}` concatenation
    preserves both."""
    return (
        f"[{idx}] (clearance: {c.classification}, dept: {c.department}, "
        f"effective: {c.effective_date.isoformat()}, doc: \"{c.document_title}\")\n"
        f"{c.snippet}"
    )


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
    conflicts_block_text = render_conflicts_block(conflicts_with_markers) or "(none)"

    # Pre-substitute the conflicts block so only {context_str} and {query_str}
    # remain as live placeholders for CompactAndRefine.
    qa_template_str = ANSWER_TEMPLATE_STR.replace(
        "{conflicts_str}", _escape_template_braces(conflicts_block_text)
    )

    text_qa_template = PromptTemplate(qa_template_str)
    refine_template = PromptTemplate(REFINE_TEMPLATE_STR)

    adapter = HolocronGroqLLM(inner_client=llm)
    synthesizer = CompactAndRefine(
        llm=adapter,
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        streaming=False,
    )

    nodes = [
        NodeWithScore(
            node=TextNode(text=_render_one_chunk(i, chunk), id_=str(chunk.chunk_id)),
            score=1.0,
        )
        for i, chunk in enumerate(chunks, start=1)
    ]

    try:
        response = await synthesizer.asynthesize(query=query, nodes=nodes)
    except LLMUnavailable:
        raise
    except Exception as e:
        raise LLMUnavailable(f"synthesizer failed: {e}") from e

    text = response.response or ""
    cited_indices = parse_citation_markers(text, total_chunks=len(chunks))
    cited_chunk_ids = [chunks[i - 1].chunk_id for i in cited_indices]

    return AnswerWithCitations(
        text=text, cited_chunk_ids=cited_chunk_ids, conflicts=conflicts_with_markers
    )
