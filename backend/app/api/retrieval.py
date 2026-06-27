from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import RefusalSummary, SearchRequest, SearchResponseBody, SearchResultItem
from app.core.clearance import ClearanceContext
from app.core.database import get_session
from app.core.tenant import get_tenant_context
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder
from app.services.retrieval import search

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=SearchResponseBody)
async def post_search(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
    tenant_ctx=Depends(get_tenant_context),
    embedder: EmbeddingProvider = Depends(get_default_embedder),
) -> SearchResponseBody:
    ctx = ClearanceContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        max_clearance=tenant_ctx.max_clearance,
        departments=tuple(tenant_ctx.departments),
    )
    response = await search(
        session=session, ctx=ctx, embedder=embedder,
        query=body.query, top_k=body.top_k,
    )
    return SearchResponseBody(
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id, document_id=r.document_id,
                document_title=r.document_title, classification=r.classification,
                department=r.department, effective_date=r.effective_date,
                snippet=r.snippet, score=r.score, rank=r.rank,
            )
            for r in response.results
        ],
        refusal=(
            RefusalSummary(
                withheld_count=response.refusal.withheld_count,
                reference_id=response.refusal.reference_id,
            )
            if response.refusal else None
        ),
    )
