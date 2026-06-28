import datetime as dt
import uuid

import pytest

from app.domain.models import AuditEvent, Chunk, Document


@pytest.mark.asyncio
async def test_can_insert_and_read_document(db_session, empire_tenant):
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        title="Employee Handbook",
        source_uri="corpus/hr/employee_handbook_2019.md",
        classification="public",
        department="hr",
        version="1.0",
        effective_date=dt.date(2019, 4, 12),
        lineage_id=uuid.uuid4(),
    )
    db_session.add(doc)
    await db_session.flush()
    assert doc.id is not None


@pytest.mark.asyncio
async def test_can_insert_and_read_chunk(db_session, empire_tenant):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    db_session.add(
        Document(
            id=doc_id,
            tenant_id=empire_tenant.id,
            title="t",
            classification="public",
            department="hr",
            version="1.0",
            effective_date=dt.date(2019, 1, 1),
            lineage_id=lineage,
        )
    )
    await db_session.flush()

    chunk = Chunk(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        document_id=doc_id,
        ordinal=0,
        text_="hello world",
        embedding=[0.1] * 768,
        classification="public",
        department="hr",
        effective_date=dt.date(2019, 1, 1),
        lineage_id=lineage,
    )
    db_session.add(chunk)
    await db_session.flush()
    assert chunk.id is not None
    assert chunk.entities == []


@pytest.mark.asyncio
async def test_can_insert_audit_event(db_session, empire_tenant):
    evt = AuditEvent(
        tenant_id=empire_tenant.id,
        user_id=uuid.uuid4(),
        correlation_id=uuid.uuid4(),
        event_type="query",
        query_text="hello",
        retrieved_ids=[uuid.uuid4()],
    )
    db_session.add(evt)
    await db_session.flush()
    assert evt.id is not None  # BIGSERIAL auto-assigned
