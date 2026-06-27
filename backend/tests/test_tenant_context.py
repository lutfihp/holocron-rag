import uuid

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import encode_session_token, hash_password
from app.core.tenant import TenantContext, get_tenant_context
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import User


@pytest_asyncio.fixture
async def app_with_probe(db_session):
    from app.core.database import get_session

    async def _override():
        yield db_session

    app = FastAPI()
    app.dependency_overrides[get_session] = _override

    @app.get("/probe")
    async def probe(ctx: TenantContext = Depends(get_tenant_context)):
        return {
            "tenant_id": str(ctx.tenant_id),
            "user_id": str(ctx.user_id),
            "max_clearance": ctx.max_clearance,
            "departments": ctx.departments,
        }

    return app


@pytest.mark.asyncio
async def test_tenant_context_extracted_from_session_cookie(
    app_with_probe, db_session, empire_tenant
):
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="dir-001",
        password_hash=hash_password("p"),
        role=Role.DIRECTOR.value,
        max_clearance=ClearanceLevel.SECRET.value,
        departments=["engineering"],
    )
    db_session.add(u)
    await db_session.flush()

    token = encode_session_token(user_id=u.id, tenant_id=empire_tenant.id)
    transport = ASGITransport(app=app_with_probe)
    async with AsyncClient(transport=transport, base_url="http://test", cookies={"holocron_session": token}) as ac:
        r = await ac.get("/probe")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(empire_tenant.id)
    assert body["max_clearance"] == "secret"
    assert body["departments"] == ["engineering"]


@pytest.mark.asyncio
async def test_tenant_context_missing_cookie_is_401(app_with_probe):
    transport = ASGITransport(app=app_with_probe)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/probe")
    assert r.status_code == 401
