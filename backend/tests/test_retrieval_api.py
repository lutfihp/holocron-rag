import datetime as dt
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Chunk, Document, User
from app.main import app
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder


@pytest_asyncio.fixture
async def client(db_session):
    from app.core.database import get_session

    async def _override_session():
        yield db_session

    fake = FakeEmbeddingProvider()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_default_embedder] = lambda: fake
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_user_and_chunks(
    db_session, empire_tenant, *, username, role, max_clearance, departments, chunks,
):
    user = User(
        id=uuid.uuid4(), tenant_id=empire_tenant.id, username=username,
        password_hash=hash_password("imperial-march"),
        role=role.value, max_clearance=max_clearance.value, departments=departments,
    )
    db_session.add(user)
    await db_session.flush()

    fake = FakeEmbeddingProvider()
    for text, classification, department in chunks:
        doc_id = uuid.uuid4()
        lineage = uuid.uuid4()
        db_session.add(
            Document(
                id=doc_id, tenant_id=empire_tenant.id, title=f"doc {text[:10]}",
                source_uri=f"corpus/{department}/x.md", classification=classification,
                department=department, version="1.0",
                effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
            )
        )
        await db_session.flush()
        db_session.add(
            Chunk(
                id=uuid.uuid4(), tenant_id=empire_tenant.id, document_id=doc_id,
                ordinal=0, text_=text, embedding=fake.embed_one(text).tolist(),
                classification=classification, department=department,
                effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
            )
        )
    await db_session.flush()
    return user


async def _login(client, empire_tenant, username):
    return await client.post(
        "/auth/login",
        json={
            "tenant_id": str(empire_tenant.id),
            "username": username,
            "password": "imperial-march",
        },
    )


@pytest.mark.asyncio
async def test_search_unauthenticated_returns_401(client):
    resp = await client.post("/retrieval/search", json={"query": "anything"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query_returns_422(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="employee.security", role=Role.EMPLOYEE,
        max_clearance=ClearanceLevel.PUBLIC, departments=["security"],
        chunks=[("anything", "public", "security")],
    )
    await _login(client, empire_tenant, "employee.security")
    resp = await client.post("/retrieval/search", json={"query": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_employee_sees_public_only_and_gets_refusal(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="employee.security", role=Role.EMPLOYEE,
        max_clearance=ClearanceLevel.PUBLIC, departments=["security"],
        chunks=[
            ("dress code applies to all imperial personnel", "public", "hr"),
            ("executive dress code exception protocols", "secret", "hr"),
        ],
    )
    await _login(client, empire_tenant, "employee.security")
    resp = await client.post("/retrieval/search", json={"query": "dress code"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(r["classification"] == "public" for r in body["results"])
    assert body["refusal"] is not None
    assert body["refusal"]["withheld_count"] >= 1
    assert "-" in body["refusal"]["reference_id"]


@pytest.mark.asyncio
async def test_search_executive_no_refusal(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="executive.fleet", role=Role.EXECUTIVE,
        max_clearance=ClearanceLevel.TOP_SECRET,
        departments=["fleet_operations", "security", "hr"],
        chunks=[
            ("dress code applies to all imperial personnel", "public", "hr"),
            ("executive dress code exception protocols", "secret", "hr"),
        ],
    )
    await _login(client, empire_tenant, "executive.fleet")
    resp = await client.post("/retrieval/search", json={"query": "dress code"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) >= 2
    assert body["refusal"] is None
