from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent, Tenant
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_response_writes_row(db_session, empire_tenant: Tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    await repo.insert_response(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        correlation_id=uuid.uuid4(),
        response_text="The answer.",
        conflicts_found={"count": 1, "subjects": ["dress code"]},
        latency_ms=412,
    )
    await db_session.flush()
    rows = (await db_session.execute(
        select(AuditEvent).where(AuditEvent.event_type == "response")
    )).scalars().all()
    assert len(rows) == 1
    r = rows[0]
    assert r.response_text == "The answer."
    assert r.conflicts_found == {"count": 1, "subjects": ["dress code"]}
    assert r.latency_ms == 412
