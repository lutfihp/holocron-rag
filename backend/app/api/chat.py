from __future__ import annotations

import uuid
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AnswerOut,
    ChatRequest,
    ChatResponse,
    CitationOut,
    ConflictOut,
    PositionOut,
    RefusalOut,
)
from app.core.clearance import ClearanceContext
from app.core.database import get_session
from app.core.tenant import get_tenant_context
from app.repositories.audit_repository import AuditRepository
from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import (
    LLMClient,
    LLMUnavailable,
    get_default_llm,
)
from app.services.conflict_detection import detect_conflicts
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder
from app.services.retrieval import search

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
async def post_ask(
    body: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    tenant_ctx=Depends(get_tenant_context),
    embedder: EmbeddingProvider = Depends(get_default_embedder),
    llm: LLMClient = Depends(get_default_llm),
) -> ChatResponse:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")

    # Middleware bound this on request.state; falls back to a fresh UUID if the
    # router is called outside the normal middleware stack (rare; defensive).
    correlation_id = getattr(request.state, "correlation_id", None) or uuid.uuid4()

    ctx = ClearanceContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        max_clearance=tenant_ctx.max_clearance,
        departments=tuple(tenant_ctx.departments),
    )

    t0 = perf_counter()
    search_resp = await search(
        session=session,
        ctx=ctx,
        embedder=embedder,
        query=body.query,
        correlation_id=correlation_id,
        top_k=body.top_k,
    )
    results = list(search_resp.results)

    conflicts = await detect_conflicts(results=results, llm=llm)

    try:
        answer = await generate_answer(
            query=body.query, chunks=results, conflicts=conflicts, llm=llm,
        )
    except LLMUnavailable as e:
        raise HTTPException(
            status_code=503, detail="LLM temporarily unavailable. Please retry."
        ) from e

    latency_ms = int((perf_counter() - t0) * 1000)

    cited_set = set(answer.cited_chunk_ids)
    citations: list[CitationOut] = []
    for i, r in enumerate(results, start=1):
        if r.chunk_id not in cited_set:
            continue
        citations.append(
            CitationOut(
                marker=i,
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                classification=r.classification,
                department=r.department,
                effective_date=r.effective_date,
                snippet=r.snippet,
                lineage_id=r.lineage_id,
            )
        )

    audit = AuditRepository(session)
    await audit.insert_response(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        correlation_id=correlation_id,
        response_text=answer.text,
        conflicts_found={
            "count": len(answer.conflicts),
            "subjects": [c.subject for c in answer.conflicts],
        },
        latency_ms=latency_ms,
    )
    await session.flush()

    return ChatResponse(
        query=body.query,
        answer=AnswerOut(text=answer.text, cited_chunk_ids=answer.cited_chunk_ids),
        citations=citations,
        conflicts=[
            ConflictOut(
                subject=c.subject,
                position_a=PositionOut(marker=c.position_a.marker, text=c.position_a.text),
                position_b=PositionOut(marker=c.position_b.marker, text=c.position_b.text),
            )
            for c in answer.conflicts
        ],
        refusal=(
            RefusalOut(
                reference_id=search_resp.refusal.reference_id,
                withheld_count=search_resp.refusal.withheld_count,
            )
            if search_resp.refusal
            else None
        ),
    )
