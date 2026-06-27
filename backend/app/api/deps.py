from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import InvalidTokenError, decode_session_token
from app.domain.models import Tenant, User
from app.repositories.user_repository import UserRepository


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> tuple[User, Tenant]:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        claims = decode_session_token(token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session") from None

    repo = UserRepository(session)
    user = await repo.get_by_id(tenant_id=claims.tenant_id, user_id=claims.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    tenant = await session.get(Tenant, claims.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tenant no longer exists")
    return user, tenant
