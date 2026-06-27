from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends

from app.api.deps import get_current_user
from app.domain.models import Tenant, User


@dataclass(frozen=True)
class TenantContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    max_clearance: str
    departments: list[str]
    role_label_map: dict[str, str]


def get_tenant_context(current: tuple[User, Tenant] = Depends(get_current_user)) -> TenantContext:
    user, tenant = current
    return TenantContext(
        tenant_id=tenant.id,
        user_id=user.id,
        role=user.role,
        max_clearance=user.max_clearance,
        departments=list(user.departments),
        role_label_map=dict(tenant.role_label_map),
    )
