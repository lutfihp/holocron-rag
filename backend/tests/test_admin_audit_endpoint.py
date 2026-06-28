from __future__ import annotations

import datetime as dt
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


# ---------- Repository tests ----------


@pytest.mark.asyncio
async def test_list_grouped_returns_one_row_per_correlation_id(
    db_session, seeded_tenant_user
):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    cid1, cid2 = uuid.uuid4(), uuid.uuid4()

    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid1,
        query_text="q1", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid1,
        response_text="r1", conflicts_found=None, latency_ms=100,
    )
    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid2,
        query_text="q2", retrieved_ids=[],
    )
    await db_session.flush()

    rows, cursor = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=50, cursor=None,
    )
    assert len(rows) == 2
    assert {r["correlation_id"] for r in rows} == {cid1, cid2}
    assert all("events" in r for r in rows)
    cid1_row = next(r for r in rows if r["correlation_id"] == cid1)
    assert cid1_row["event_count"] == 2
    assert cid1_row["latency_ms"] == 100


@pytest.mark.asyncio
async def test_list_grouped_filters_by_refusal(
    db_session, seeded_tenant_user
):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    cid1, cid2 = uuid.uuid4(), uuid.uuid4()
    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid1,
        query_text="q1", retrieved_ids=[],
    )
    await repo.insert_refusal(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid1,
        reference_id="ref", retrieved_ids=[], withheld_ids=[],
    )
    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid2,
        query_text="q2", retrieved_ids=[],
    )
    await db_session.flush()

    rows, _ = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=50, cursor=None, has_refusal=True,
    )
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == cid1
    assert rows[0]["had_refusal"] is True


@pytest.mark.asyncio
async def test_list_grouped_filters_by_conflict(
    db_session, seeded_tenant_user
):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    cid_with, cid_without = uuid.uuid4(), uuid.uuid4()
    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid_with,
        query_text="q", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid_with,
        response_text="r", conflicts_found={"count": 1, "subjects": ["x"]},
        latency_ms=200,
    )
    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid_without,
        query_text="q2", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid_without,
        response_text="r2", conflicts_found={"count": 0, "subjects": []},
        latency_ms=200,
    )
    await db_session.flush()

    rows, _ = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=50, cursor=None, has_conflict=True,
    )
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == cid_with
    assert rows[0]["had_conflict"] is True


@pytest.mark.asyncio
async def test_list_grouped_pagination_cursor_round_trips(
    db_session, seeded_tenant_user
):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    for _ in range(5):
        await repo.insert_query(
            tenant_id=tenant_id, user_id=user_id, correlation_id=uuid.uuid4(),
            query_text="q", retrieved_ids=[],
        )
    await db_session.flush()

    first, cursor = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=2, cursor=None,
    )
    assert len(first) == 2
    assert cursor is not None

    second, cursor2 = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=2, cursor=cursor,
    )
    assert len(second) == 2
    assert cursor2 is not None

    third, cursor3 = await repo.list_grouped_by_correlation(
        tenant_id=tenant_id, limit=2, cursor=cursor2,
    )
    assert len(third) == 1
    assert cursor3 is None

    # No overlap across pages
    seen = {r["correlation_id"] for r in first + second + third}
    assert len(seen) == 5


# ---------- Endpoint tests ----------


@pytest_asyncio.fixture
async def admin_user(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="executive.fleet",
        password_hash=hash_password("imperial-march"),
        role=Role.EXECUTIVE.value,
        max_clearance=ClearanceLevel.TOP_SECRET.value,
        departments=["fleet_operations", "security"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def non_admin_user(db_session, empire_tenant: Tenant) -> User:
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
async def test_admin_audit_endpoint_returns_grouped_rows(
    client, db_session, empire_tenant, admin_user
):
    # Seed two correlation groups
    repo = AuditRepository(db_session)
    cid1, cid2 = uuid.uuid4(), uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=admin_user.id, correlation_id=cid1,
        query_text="q1", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=empire_tenant.id, user_id=admin_user.id, correlation_id=cid1,
        response_text="r1", conflicts_found=None, latency_ms=42,
    )
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=admin_user.id, correlation_id=cid2,
        query_text="q2", retrieved_ids=[],
    )
    await db_session.flush()

    await _login(client, empire_tenant.id, admin_user.username)
    resp = await client.get("/admin/audit")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "rows" in body
    assert "next_cursor" in body
    assert len(body["rows"]) == 2


@pytest.mark.asyncio
async def test_admin_audit_endpoint_role_gated_for_employee(
    client, empire_tenant, non_admin_user
):
    await _login(client, empire_tenant.id, non_admin_user.username)
    resp = await client.get("/admin/audit")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_endpoint_unauthenticated_is_401(client):
    resp = await client.get("/admin/audit")
    assert resp.status_code == 401
