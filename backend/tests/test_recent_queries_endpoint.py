from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.core.security import hash_password
from app.core.warmup import WarmState
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Tenant, User
from app.main import app
from app.repositories.audit_repository import AuditRepository


@pytest_asyncio.fixture
async def some_user(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="manager.hr",
        password_hash=hash_password("imperial-march"),
        role=Role.MANAGER.value,
        max_clearance=ClearanceLevel.RESTRICTED.value,
        departments=["hr"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def other_user(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="employee.security",
        password_hash=hash_password("imperial-march"),
        role=Role.EMPLOYEE.value,
        max_clearance=ClearanceLevel.PUBLIC.value,
        departments=["security"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def client(db_session):
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login(client: AsyncClient, tenant_id, username) -> None:
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(tenant_id), "username": username, "password": "imperial-march"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_recent_queries_returns_users_own_events_only(
    client, db_session, empire_tenant, some_user, other_user
):
    repo = AuditRepository(db_session)
    # Mine
    my_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=some_user.id, correlation_id=my_cid,
        query_text="my question", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=empire_tenant.id, user_id=some_user.id, correlation_id=my_cid,
        response_text="answered", conflicts_found=None, latency_ms=123,
    )
    # Someone else's
    their_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=other_user.id, correlation_id=their_cid,
        query_text="their question", retrieved_ids=[],
    )
    await db_session.flush()

    await _login(client, empire_tenant.id, some_user.username)
    resp = await client.get("/me/recent-queries")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["query"] == "my question"
    assert item["correlation_id"] == str(my_cid)
    assert item["latency_ms"] == 123
    assert isinstance(item["occurred_at"], str)


@pytest.mark.asyncio
async def test_recent_queries_respects_limit(
    client, db_session, empire_tenant, some_user
):
    repo = AuditRepository(db_session)
    for i in range(8):
        await repo.insert_query(
            tenant_id=empire_tenant.id, user_id=some_user.id,
            correlation_id=uuid.uuid4(),
            query_text=f"q{i}", retrieved_ids=[],
        )
    await db_session.flush()

    await _login(client, empire_tenant.id, some_user.username)
    resp = await client.get("/me/recent-queries?limit=3")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_recent_queries_unauthenticated_is_401(client):
    resp = await client.get("/me/recent-queries")
    assert resp.status_code == 401
