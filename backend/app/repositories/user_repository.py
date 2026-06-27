from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, *, tenant_id: uuid.UUID, username: str) -> User | None:
        stmt = select(User).where(User.tenant_id == tenant_id, User.username == username)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, *, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.tenant_id == tenant_id, User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()
