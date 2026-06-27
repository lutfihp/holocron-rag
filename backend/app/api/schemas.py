from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    tenant_id: uuid.UUID
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TenantSummary(BaseModel):
    id: uuid.UUID
    name: str
    role_label: str  # the display label of THIS user's role in THIS tenant


class UserSummary(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    max_clearance: str
    departments: list[str]
    tenant: TenantSummary
