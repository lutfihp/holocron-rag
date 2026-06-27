import datetime as dt
import uuid

import pytest

from app.core.clearance import ClearanceContext
from app.domain.models import Chunk, Document
from app.repositories.chunk_repository import ChunkRepository


async def _make_doc_and_chunk(
    session, tenant_id, *, classification, department, text, embedding=None
):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    session.add(
        Document(
            id=doc_id,
            tenant_id=tenant_id,
            title="t",
            classification=classification,
            department=department,
            version="1.0",
            effective_date=dt.date(2020, 1, 1),
            lineage_id=lineage,
        )
    )
    await session.flush()
    chunk = Chunk(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        document_id=doc_id,
        ordinal=0,
        text_=text,
        embedding=embedding or [0.0] * 768,
        classification=classification,
        department=department,
        effective_date=dt.date(2020, 1, 1),
        lineage_id=lineage,
    )
    session.add(chunk)
    await session.flush()
    return chunk


def _ctx(tenant_id, max_clearance, departments):
    return ClearanceContext(
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        max_clearance=max_clearance,
        departments=tuple(departments),
    )


@pytest.mark.asyncio
async def test_bm25_topn_filters_by_clearance(db_session, empire_tenant):
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="hr",
        text="dress code policy applies to all",
    )
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="secret", department="hr",
        text="dress code exception protocols",
    )

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    results = await repo.bm25_topn(ctx, query="dress code", n=10)

    assert len(results) == 1
    assert results[0].classification == "public"


@pytest.mark.asyncio
async def test_bm25_topn_filters_by_department(db_session, empire_tenant):
    # public docs ARE visible regardless of department
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="engineering",
        text="public engineering memo",
    )
    # restricted requires matching department
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="restricted", department="engineering",
        text="restricted engineering memo",
    )

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "secret", ["hr"])  # HR director, no eng
    results = await repo.bm25_topn(ctx, query="engineering memo", n=10)
    classifications = sorted(r.classification for r in results)
    # restricted eng excluded; public eng included
    assert "secret" not in classifications
    assert "restricted" not in classifications
    assert "public" in classifications


@pytest.mark.asyncio
async def test_bm25_topn_tenant_scoped(db_session, empire_tenant):
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="hr",
        text="visible chunk",
    )
    repo = ChunkRepository(db_session)
    other = _ctx(uuid.uuid4(), "top_secret", ["hr"])
    assert await repo.bm25_topn(other, query="visible chunk", n=10) == []


@pytest.mark.asyncio
async def test_vector_topn_filters_by_clearance(db_session, empire_tenant):
    target = [0.1] * 768
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="hr",
        text="anything", embedding=target,
    )
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="secret", department="hr",
        text="anything else", embedding=target,
    )

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    results = await repo.vector_topn(ctx, query_vector=target, n=10)
    assert all(r.classification == "public" for r in results)


@pytest.mark.asyncio
async def test_unfiltered_topn_ids_ignores_rbac(db_session, empire_tenant):
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="hr",
        text="dress code policy",
    )
    secret = await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="top_secret", department="security",
        text="dress code clearance protocols",
    )

    repo = ChunkRepository(db_session)
    ids = await repo.unfiltered_topn_ids(
        tenant_id=empire_tenant.id,
        query="dress code",
        query_vector=[0.1] * 768,
        n=25,
    )
    assert secret.id in ids


@pytest.mark.asyncio
async def test_unfiltered_topn_ids_still_tenant_scoped(db_session, empire_tenant):
    await _make_doc_and_chunk(
        db_session, empire_tenant.id,
        classification="public", department="hr",
        text="dress code",
    )
    repo = ChunkRepository(db_session)
    ids = await repo.unfiltered_topn_ids(
        tenant_id=uuid.uuid4(),
        query="dress code",
        query_vector=[0.1] * 768,
        n=25,
    )
    assert ids == set()


@pytest.mark.asyncio
async def test_bulk_insert_chunks(db_session, empire_tenant):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    db_session.add(
        Document(
            id=doc_id, tenant_id=empire_tenant.id, title="t",
            classification="public", department="hr", version="1.0",
            effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
    )
    await db_session.flush()

    chunks = [
        Chunk(
            id=uuid.uuid4(), tenant_id=empire_tenant.id, document_id=doc_id, ordinal=i,
            text_=f"chunk {i}", embedding=[0.0] * 768, classification="public",
            department="hr", effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
        for i in range(3)
    ]
    repo = ChunkRepository(db_session)
    inserted = await repo.bulk_insert(chunks)
    assert inserted == 3
