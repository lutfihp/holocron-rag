from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clearance import ClearanceContext
from app.domain.chunk import RefusalContext, RetrievalResult, SearchResponse
from app.repositories.audit_repository import AuditRepository
from app.repositories.chunk_repository import ChunkHit, ChunkRepository
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.retrieval.refusal import record_refusal
from app.services.retrieval.rrf import rrf_fuse

CANDIDATES_PER_BRANCH = 25


async def search(
    *,
    session: AsyncSession,
    ctx: ClearanceContext,
    embedder: EmbeddingProvider,
    query: str,
    correlation_id: uuid.UUID,
    top_k: int = 6,
) -> SearchResponse:
    if not query.strip():
        raise ValueError("query must be non-empty")

    chunk_repo = ChunkRepository(session)
    audit = AuditRepository(session)

    query_vec = embedder.embed_one(query).tolist()

    bm_task = chunk_repo.bm25_topn(ctx, query=query, n=CANDIDATES_PER_BRANCH)
    vec_task = chunk_repo.vector_topn(ctx, query_vector=query_vec, n=CANDIDATES_PER_BRANCH)
    unfiltered_task = chunk_repo.unfiltered_topn_ids(
        tenant_id=ctx.tenant_id,
        query=query,
        query_vector=query_vec,
        n=CANDIDATES_PER_BRANCH,
    )
    bm_hits, vec_hits, unfiltered_ids = await asyncio.gather(
        bm_task, vec_task, unfiltered_task
    )

    fused = rrf_fuse(
        [(h.chunk_id, h.rank) for h in bm_hits],
        [(h.chunk_id, h.rank) for h in vec_hits],
        k=60,
    )

    by_id: dict = {h.chunk_id: h for h in bm_hits}
    for h in vec_hits:
        by_id.setdefault(h.chunk_id, h)

    results: list[RetrievalResult] = []
    for fused_rank, (chunk_id, score) in enumerate(fused[:top_k], start=1):
        h: ChunkHit = by_id[chunk_id]
        results.append(
            RetrievalResult(
                chunk_id=h.chunk_id, document_id=h.document_id,
                document_title=h.document_title, classification=h.classification,
                department=h.department, effective_date=h.effective_date,
                snippet=h.snippet, score=score, rank=fused_rank,
                lineage_id=h.lineage_id, entities=tuple(h.entities or ()),
            )
        )

    filtered_ids = set(by_id.keys())
    withheld_ids = list(unfiltered_ids - filtered_ids)

    refusal: RefusalContext | None = None
    retrieved_for_audit = [r.chunk_id for r in results]
    if withheld_ids:
        ref = await record_refusal(
            audit,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            correlation_id=correlation_id,
            retrieved_ids=retrieved_for_audit,
            withheld_ids=withheld_ids,
        )
        refusal = RefusalContext(
            reference_id=ref,
            withheld_count=len(withheld_ids),
            withheld_ids=tuple(withheld_ids),
        )

    await audit.insert_query(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        correlation_id=correlation_id,
        query_text=query,
        retrieved_ids=retrieved_for_audit,
    )

    return SearchResponse(results=tuple(results), refusal=refusal)
