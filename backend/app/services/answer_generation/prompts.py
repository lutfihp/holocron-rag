from __future__ import annotations

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict


ANSWER_TEMPLATE_STR = """You are HOLOCRON, an enterprise knowledge assistant for the Imperial archives.
Answer the user's question using ONLY the numbered context blocks below.

Rules:
- Cite every claim with inline markers like [1], [2]. A claim may have multiple markers.
- Do NOT use information not present in the context.
- If the context is insufficient to answer, say so explicitly.
- When the CONFLICTS section is non-empty, acknowledge the disagreement with phrasing like:
  "Sources disagree: [n] states X; [m] states Y."
- Be concise. 3 to 5 sentences for typical questions.

CONTEXT:
{context_str}

CONFLICTS:
{conflicts_str}

QUESTION: {query_str}

ANSWER:"""


REFINE_TEMPLATE_STR = """An initial answer exists for the question.

Existing answer:
{existing_answer}

New context to consider:
{context_msg}

Refine the existing answer to incorporate the new context if relevant. Preserve all existing [n] citation markers; add new ones only for newly cited content. Do not introduce claims absent from the context. If the new context is irrelevant, return the existing answer unchanged.

QUESTION: {query_str}

REFINED ANSWER:"""


def render_context_block(chunks: list[RetrievalResult]) -> str:
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] (clearance: {c.classification}, dept: {c.department}, "
            f"effective: {c.effective_date.isoformat()}, doc: \"{c.document_title}\")\n"
            f"{c.snippet}"
        )
    return "\n\n".join(parts)


def render_conflicts_block(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return ""
    parts: list[str] = []
    for c in conflicts:
        parts.append(
            f"- Subject: {c.subject}\n"
            f"  [{c.position_a.marker}] states: {c.position_a.text}\n"
            f"  [{c.position_b.marker}] states: {c.position_b.text}"
        )
    return "\n".join(parts)
