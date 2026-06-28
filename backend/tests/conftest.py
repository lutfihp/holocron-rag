from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.domain.models import Base, Tenant


@pytest.fixture(autouse=True)
def _clear_judge_cache():
    """Phase D: module-global conflict-judge cache must not leak across tests.

    Without this autouse, tests that exercise judge.py reuse cache entries
    seeded by earlier tests, producing flake on test re-ordering. Cheap and
    idempotent — safe to run before every test.
    """
    from app.services.conflict_detection.judge import _judge_cache_clear
    _judge_cache_clear()
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-test AsyncSession on the test database. Drops & recreates the schema
    each test so there's no cross-test state and no event-loop sharing issues
    with asyncpg on Windows."""
    settings = get_settings()
    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(bind=engine, expire_on_commit=False)
        session = Session()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def empire_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Galactic Empire",
        role_label_map={
            "employee": "Imperial Employee",
            "manager": "Imperial Manager",
            "director": "Imperial Director",
            "executive": "Imperial Executive",
        },
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant
