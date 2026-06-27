import pytest
from sqlalchemy import text

from app.core.database import get_engine


@pytest.mark.asyncio
async def test_engine_can_execute_simple_query():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS one"))
        assert result.scalar_one() == 1
