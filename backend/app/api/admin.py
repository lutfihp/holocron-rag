from __future__ import annotations

import datetime as _dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.tenant import TenantContext, get_tenant_context
from app.repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/admin", tags=["admin"])

_ALLOWED_ROLES = {"director", "executive"}


def _require_admin(tenant_ctx: TenantContext) -> None:
    if tenant_ctx.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="admin access required")


@router.get("/audit")
async def get_audit(
    cursor: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    start: _dt.datetime | None = Query(default=None),
    end: _dt.datetime | None = Query(default=None),
    has_refusal: bool | None = Query(default=None),
    has_conflict: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    _require_admin(tenant_ctx)
    repo = AuditRepository(session)
    user_uuid = uuid.UUID(user_id) if user_id else None
    rows, next_cursor = await repo.list_grouped_by_correlation(
        tenant_id=tenant_ctx.tenant_id,
        limit=limit,
        cursor=cursor,
        user_id=user_uuid,
        start=start,
        end=end,
        has_refusal=has_refusal,
        has_conflict=has_conflict,
    )
    for r in rows:
        r["correlation_id"] = str(r["correlation_id"])
        if r["user_id"]:
            r["user_id"] = str(r["user_id"])
    return {"rows": rows, "next_cursor": next_cursor}


@router.get("/audit/summary")
async def audit_summary(
    session: AsyncSession = Depends(get_session),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, int]:
    _require_admin(tenant_ctx)
    repo = AuditRepository(session)
    today = _dt.datetime.now(_dt.timezone.utc).date()
    return await repo.summary_counts(tenant_id=tenant_ctx.tenant_id, day_utc=today)
