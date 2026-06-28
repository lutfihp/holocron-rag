from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_query_persists_correlation_id(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    cid = uuid.uuid4()
    repo = AuditRepository(db_session)

    await repo.insert_query(
        tenant_id=tenant_id,
        user_id=user_id,
        correlation_id=cid,
        query_text="who runs hr?",
        retrieved_ids=[],
    )
    await db_session.flush()

    row = (await db_session.execute(select(AuditEvent))).scalar_one()
    assert row.correlation_id == cid
    assert row.event_type == "query"


@pytest.mark.asyncio
async def test_three_events_share_one_correlation_id(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    cid = uuid.uuid4()
    repo = AuditRepository(db_session)

    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        query_text="q", retrieved_ids=[],
    )
    await repo.insert_refusal(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        reference_id="ref", retrieved_ids=[], withheld_ids=[],
    )
    await repo.insert_response(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        response_text="r", conflicts_found=None, latency_ms=42,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 3
    assert {r.correlation_id for r in rows} == {cid}
