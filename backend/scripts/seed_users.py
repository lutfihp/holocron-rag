"""Seed the Galactic Empire tenant and one demo user per (role x department) cell.

Run via `make backend-seed` (or `python scripts/seed_users.py` from `backend/`
with the venv active). Idempotent: safe to re-run.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import get_sessionmaker
from app.core.security import hash_password
from app.domain.enums import Department, Role
from app.domain.models import Tenant, User

EMPIRE_NAME = "Galactic Empire"
ROLE_LABEL_MAP = {
    Role.EMPLOYEE.value: "Imperial Employee",
    Role.MANAGER.value: "Imperial Manager",
    Role.DIRECTOR.value: "Imperial Director",
    Role.EXECUTIVE.value: "Imperial Executive",
}
DEFAULT_PASSWORD = "imperial-march"  # seed-only; rotate before any non-local exposure


@dataclass(frozen=True)
class SeedUser:
    username: str
    role: Role
    departments: list[Department]


SEED_USERS: list[SeedUser] = [
    SeedUser("employee.security", Role.EMPLOYEE, [Department.SECURITY]),
    SeedUser("employee.engineering", Role.EMPLOYEE, [Department.ENGINEERING]),
    SeedUser("manager.hr", Role.MANAGER, [Department.HR]),
    SeedUser("manager.engineering", Role.MANAGER, [Department.ENGINEERING]),
    SeedUser("director.engineering", Role.DIRECTOR, [Department.ENGINEERING]),
    SeedUser("director.security", Role.DIRECTOR, [Department.SECURITY]),
    SeedUser("executive.fleet", Role.EXECUTIVE, [Department.FLEET_OPERATIONS, Department.SECURITY]),
    SeedUser("executive.procurement", Role.EXECUTIVE, [Department.PROCUREMENT, Department.HR]),
]


async def _upsert_tenant(session) -> Tenant:
    stmt = select(Tenant).where(Tenant.name == EMPIRE_NAME)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.role_label_map = ROLE_LABEL_MAP
        return existing
    t = Tenant(id=uuid.uuid4(), name=EMPIRE_NAME, role_label_map=ROLE_LABEL_MAP)
    session.add(t)
    await session.flush()
    return t


async def _upsert_user(session, tenant: Tenant, spec: SeedUser) -> None:
    stmt = select(User).where(User.tenant_id == tenant.id, User.username == spec.username)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    departments = [d.value for d in spec.departments]
    if existing:
        existing.role = spec.role.value
        existing.max_clearance = spec.role.max_clearance().value
        existing.departments = departments
        existing.password_hash = hash_password(DEFAULT_PASSWORD)
        return
    session.add(
        User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            username=spec.username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=spec.role.value,
            max_clearance=spec.role.max_clearance().value,
            departments=departments,
        )
    )


async def main() -> int:
    Session = get_sessionmaker()
    async with Session() as session:
        tenant = await _upsert_tenant(session)
        for spec in SEED_USERS:
            await _upsert_user(session, tenant, spec)
        await session.commit()

    print(f"Seeded tenant '{EMPIRE_NAME}' (id={tenant.id}).")
    print(f"Password for all demo accounts: {DEFAULT_PASSWORD!r}")
    print("Users:")
    for spec in SEED_USERS:
        depts = ",".join(d.value for d in spec.departments)
        print(f"  {spec.username:<28} role={spec.role.value:<10} depts={depts}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
