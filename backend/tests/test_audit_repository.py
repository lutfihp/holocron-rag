import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_query_event(db_session, empire_tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    retrieved = [uuid.uuid4(), uuid.uuid4()]
    await repo.insert_query(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        query_text="dress code policy",
        retrieved_ids=retrieved,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "query"
    assert rows[0].retrieved_ids == retrieved


@pytest.mark.asyncio
async def test_insert_refusal_event(db_session, empire_tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    withheld = [uuid.uuid4(), uuid.uuid4()]
    await repo.insert_refusal(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        reference_id="A7F2-CXJK",
        retrieved_ids=[],
        withheld_ids=withheld,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "refusal"
    assert rows[0].refusal_ref == "A7F2-CXJK"
    assert rows[0].withheld_ids == withheld
