import re
import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository
from app.services.retrieval.refusal import generate_reference_id, record_refusal


def test_reference_id_format():
    ref = generate_reference_id()
    assert re.fullmatch(r"[A-Z2-7]{4}-[A-Z2-7]{4}", ref)


def test_reference_id_is_random():
    ids = {generate_reference_id() for _ in range(50)}
    assert len(ids) > 45  # tolerate astronomically unlikely collision


@pytest.mark.asyncio
async def test_record_refusal_persists_audit_row(db_session, empire_tenant):
    audit = AuditRepository(db_session)
    user = uuid.uuid4()
    withheld = [uuid.uuid4(), uuid.uuid4()]
    ref = await record_refusal(
        audit,
        tenant_id=empire_tenant.id,
        user_id=user,
        retrieved_ids=[],
        withheld_ids=withheld,
    )
    await db_session.flush()
    assert re.fullmatch(r"[A-Z2-7]{4}-[A-Z2-7]{4}", ref)

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].refusal_ref == ref
    assert rows[0].withheld_ids == withheld
