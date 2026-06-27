from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, TenantSummary, UserSummary
from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import encode_session_token, verify_password
from app.domain.models import Tenant, User
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_user_summary(user: User, tenant: Tenant) -> UserSummary:
    label = tenant.role_label_map.get(user.role, user.role)
    return UserSummary(
        id=user.id,
        username=user.username,
        role=user.role,
        max_clearance=user.max_clearance,
        departments=list(user.departments),
        tenant=TenantSummary(id=tenant.id, name=tenant.name, role_label=label),
    )


@router.post("/login", response_model=UserSummary)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserSummary:
    tenant = await session.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    repo = UserRepository(session)
    user = await repo.get_by_username(tenant_id=body.tenant_id, username=body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

    settings = get_settings()
    token = encode_session_token(user_id=user.id, tenant_id=user.tenant_id)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_ttl_hours * 3600,
        path="/",
    )
    return _build_user_summary(user, tenant)


@router.get("/me", response_model=UserSummary)
async def me(current: tuple[User, Tenant] = Depends(get_current_user)) -> UserSummary:
    user, tenant = current
    return _build_user_summary(user, tenant)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout() -> Response:
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie(key=get_settings().cookie_name, path="/")
    return resp
