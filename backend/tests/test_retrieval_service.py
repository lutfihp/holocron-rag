import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app.core.clearance import ClearanceContext
from app.domain.models import AuditEvent, Chunk, Document
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.retrieval import search


async def _seed(session, tenant_id, *, text, classification, department, embedder):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    session.add(
        Document(
            id=doc_id, tenant_id=tenant_id, title=f"doc {text[:10]}",
            source_uri=f"corpus/{department}/x.md", classification=classification,
            department=department, version="1", effective_date=dt.date(2020, 1, 1),
            lineage_id=lineage,
        )
    )
    await session.flush()
    session.add(
        Chunk(
            id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, ordinal=0,
            text_=text, embedding=embedder.embed_one(text).tolist(),
            classification=classification, department=department,
            effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
    )
    await session.flush()
    return doc_id


def _ctx(tenant_id, max_clearance, departments, user_id=None):
    return ClearanceContext(
        tenant_id=tenant_id,
        user_id=user_id or uuid.uuid4(),
        max_clearance=max_clearance,
        departments=tuple(departments),
    )


@pytest.mark.asyncio
async def test_search_returns_only_allowed_results(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="dress code applies to all imperial personnel",
                classification="public", department="hr", embedder=fake)
    await _seed(db_session, empire_tenant.id, text="executive dress code exception protocols",
                classification="secret", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    response = await search(
        session=db_session, ctx=ctx, embedder=fake, query="dress code", correlation_id=uuid.uuid4(), top_k=6
    )
    assert all(r.classification == "public" for r in response.results)
    assert response.refusal is not None
    assert response.refusal.withheld_count >= 1


@pytest.mark.asyncio
async def test_search_no_refusal_when_executive(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="dress code applies to all imperial personnel",
                classification="public", department="hr", embedder=fake)
    await _seed(db_session, empire_tenant.id, text="executive dress code exception protocols",
                classification="secret", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "top_secret", ["hr"])
    response = await search(
        session=db_session, ctx=ctx, embedder=fake, query="dress code", correlation_id=uuid.uuid4(), top_k=6
    )
    assert len(response.results) >= 2
    assert response.refusal is None


@pytest.mark.asyncio
async def test_search_writes_query_audit_row(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="public chunk",
                classification="public", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    await search(session=db_session, ctx=ctx, embedder=fake, query="public", correlation_id=uuid.uuid4(), top_k=6)
    await db_session.flush()

    rows = (
        await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "query"))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].query_text == "public"
