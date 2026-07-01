from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.tenant import TenantContext, get_tenant_context
from app.repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/recent-queries")
async def recent_queries(
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    repo = AuditRepository(session)
    items = await repo.list_recent_queries(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        limit=limit,
    )
    serialized = []
    for i in items:
        serialized.append({
            "correlation_id": str(i["correlation_id"]),
            "query": i["query"],
            "occurred_at": i["occurred_at"].isoformat(),
            "latency_ms": i["latency_ms"],
        })
    return {"items": serialized}
