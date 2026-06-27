import uuid

import pytest

from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import User
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_by_username_returns_none_when_missing(db_session, empire_tenant):
    repo = UserRepository(db_session)
    found = await repo.get_by_username(tenant_id=empire_tenant.id, username="nobody")
    assert found is None


@pytest.mark.asyncio
async def test_get_by_username_returns_user(db_session, empire_tenant):
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="ts-001",
        password_hash=hash_password("p"),
        role=Role.EMPLOYEE.value,
        max_clearance=ClearanceLevel.PUBLIC.value,
        departments=["security"],
    )
    db_session.add(u)
    await db_session.flush()

    repo = UserRepository(db_session)
    found = await repo.get_by_username(tenant_id=empire_tenant.id, username="ts-001")
    assert found is not None
    assert found.id == u.id
    assert found.departments == ["security"]


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_tenant(db_session, empire_tenant):
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="exec-001",
        password_hash=hash_password("p"),
        role=Role.EXECUTIVE.value,
        max_clearance=ClearanceLevel.TOP_SECRET.value,
        departments=["security", "fleet_operations"],
    )
    db_session.add(u)
    await db_session.flush()

    repo = UserRepository(db_session)
    found = await repo.get_by_id(tenant_id=empire_tenant.id, user_id=u.id)
    assert found is not None
    other_tenant = uuid.uuid4()
    not_found = await repo.get_by_id(tenant_id=other_tenant, user_id=u.id)
    assert not_found is None
