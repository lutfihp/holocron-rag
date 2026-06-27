import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import User
from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    from app.core.database import get_session

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_employee(db_session, empire_tenant):
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="ts-001",
        password_hash=hash_password("imperial-march"),
        role=Role.EMPLOYEE.value,
        max_clearance=ClearanceLevel.PUBLIC.value,
        departments=["security"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_login_success_sets_cookie_and_returns_user(client, empire_tenant, seeded_employee):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "ts-001"
    assert body["role"] == "employee"
    assert body["max_clearance"] == "public"
    assert body["departments"] == ["security"]
    assert body["tenant"]["name"] == "Galactic Empire"
    assert body["tenant"]["role_label"] == "Imperial Employee"
    assert "holocron_session" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, empire_tenant, seeded_employee):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client, empire_tenant):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ghost", "password": "x"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user_when_authed(client, empire_tenant, seeded_employee):
    login = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    assert login.status_code == 200

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "ts-001"


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_subsequent_me_is_401(client, empire_tenant, seeded_employee):
    await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    logout = await client.delete("/auth/session")
    assert logout.status_code == 204

    me = await client.get("/auth/me")
    assert me.status_code == 401
