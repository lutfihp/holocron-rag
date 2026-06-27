import datetime as dt
import uuid

import pytest

from app.domain.models import Document
from app.repositories.document_repository import DocumentRepository


def _make_doc(
    tenant_id,
    *,
    title="t",
    department="hr",
    classification="public",
    source_uri="corpus/hr/t.md",
    lineage_id=None,
):
    return Document(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title=title,
        source_uri=source_uri,
        classification=classification,
        department=department,
        version="1.0",
        effective_date=dt.date(2020, 1, 1),
        lineage_id=lineage_id or uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_insert_and_get_by_id(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    doc = _make_doc(empire_tenant.id)
    await repo.insert(doc)

    fetched = await repo.get_by_id(tenant_id=empire_tenant.id, document_id=doc.id)
    assert fetched is not None
    assert fetched.title == "t"


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_tenant(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    doc = _make_doc(empire_tenant.id)
    await repo.insert(doc)

    other_tenant = uuid.uuid4()
    assert await repo.get_by_id(tenant_id=other_tenant, document_id=doc.id) is None


@pytest.mark.asyncio
async def test_delete_by_source_uri_prefix(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    await repo.insert(_make_doc(empire_tenant.id, source_uri="corpus/hr/a.md"))
    await repo.insert(_make_doc(empire_tenant.id, source_uri="corpus/eng/b.md"))
    await repo.insert(_make_doc(empire_tenant.id, source_uri="other/c.md"))
    await db_session.flush()

    deleted = await repo.delete_by_source_prefix(tenant_id=empire_tenant.id, prefix="corpus/")
    assert deleted == 2
