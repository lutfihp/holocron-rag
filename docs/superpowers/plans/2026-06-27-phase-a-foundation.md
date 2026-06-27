# HOLOCRON — Phase A (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the repository skeleton, database schema, auth, and a minimal login flow so a user can `docker compose up`, log in as different Imperial roles, and see their clearance tier rendered in the UI.

**Architecture:** A FastAPI backend (Python 3.12, async SQLAlchemy 2.x, Pydantic v2) talks to Postgres 16 (+ pgvector + tsvector, both enabled now even though they're exercised in later phases). Auth is JWT in an HttpOnly cookie. A Next.js 15 / TS frontend (App Router + Tailwind + shadcn/ui) renders `/login` and `/me`. The data model is multi-tenant from day one (every row carries `tenant_id`), but only one tenant (the Galactic Empire) is seeded in Phase A. Roles on `users` are tenant-agnostic (`employee | manager | director | executive`); per-tenant display labels live in `tenants.role_label_map`.

**Tech Stack:** Python 3.11 (pip + venv), FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, pgvector, bcrypt, PyJWT, pydantic-settings, pytest + pytest-asyncio + httpx. Next.js 15, TypeScript, Tailwind v3, shadcn/ui. Postgres 16 + pgvector + Redis via Docker Compose. pnpm for JS.

**Reference:** Spec at `docs/superpowers/specs/2026-06-27-holocron-design.md` — particularly §5 (data model), §10.1 (Phase A deliverables), §13 (DoD).

---

## Engineer Onboarding (read once before Task 1)

- **Working directory** is `d:/Codading Repo/holocron/` (Windows). Use POSIX-style paths in commands where the tool accepts them; otherwise use Windows paths.
- **Shell** is PowerShell. POSIX commands shown below also work in Git Bash if you prefer.
- **Folder is not yet a git repository.** Task 1 initializes it.
- **Python 3.11** must be on PATH. We use `python -m venv` + `pip` (no `uv`).
- **Activate the venv** once per shell session before running any backend command:
  - PowerShell: `.\.venv\Scripts\Activate.ps1` (one-time setup may need `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)
  - Git Bash: `source .venv/Scripts/activate`
  - cmd: `.venv\Scripts\activate.bat`
  All commands in tasks below assume the venv is active. If you forget, prepend `.venv/Scripts/` (Windows) or `.venv/bin/` (POSIX) to `python`, `pytest`, `alembic`, `uvicorn`.
- **pnpm** for JS. Install from <https://pnpm.io/installation> if needed.
- **Docker Desktop** must be running.
- **Conventional Commits** for all commit messages (`feat:`, `chore:`, `test:`, `fix:`, `docs:`, `refactor:`).
- Every code-changing task ends with a commit step. Don't batch.
- Tests use a real Postgres database (`holocron_test`) on the same Docker Postgres. Do not introduce SQLite — pgvector & tsvector features differ.

---

## File Layout Produced by This Plan

```
holocron/
├── .gitignore
├── README.md
├── Makefile
├── docker-compose.yml
├── docs/superpowers/{specs,plans}/                  # already exists
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── .env.example
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_phase_a_initial.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── tenant.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py
│   │   │   └── models.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── user_repository.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── deps.py
│   │       ├── schemas.py
│   │       └── auth.py
│   ├── scripts/
│   │   └── seed_users.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_security.py
│       ├── test_user_repository.py
│       ├── test_auth_api.py
│       └── test_tenant_context.py
└── frontend/
    ├── package.json
    ├── pnpm-lock.yaml
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.mjs
    ├── components.json
    ├── Dockerfile
    ├── .env.local.example
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── login/page.tsx
    │   └── me/page.tsx
    ├── components/
    │   ├── ui/                              # shadcn-generated
    │   └── ClearanceBadge.tsx
    └── lib/
        ├── api.ts
        └── types.ts
```

Each file has one responsibility. Files that change together live together (e.g., all auth-API concerns in `app/api/auth.py`). Anything that grows beyond ~250 lines is a signal to split — flag it but don't refactor in this phase.

---

## Task 1: Repo init + .gitignore + README + Makefile skeleton

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `Makefile`

- [ ] **Step 1: Initialize git repo**

```powershell
git init
git branch -M main
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
.next/
.turbo/
*.log
pnpm-debug.log*

# Env & secrets
.env
.env.local
.env.*.local
!*.example

# OS / IDE
.DS_Store
Thumbs.db
.vscode/
.idea/

# Build artifacts
dist/
build/
```

- [ ] **Step 3: Create `README.md` skeleton**

```markdown
# HOLOCRON

Classification-aware enterprise RAG over a synthetic Galactic Empire corpus.
See `docs/superpowers/specs/2026-06-27-holocron-design.md` for the design.

## Quickstart (Phase A)

```bash
docker compose up -d postgres redis
make backend-install
make backend-migrate
make backend-seed
make dev
```

Then open <http://localhost:3000>, log in with one of the seeded accounts
(see `make backend-seed` output), and visit `/me`.

## Layout

- `backend/` — FastAPI + SQLAlchemy + Alembic
- `frontend/` — Next.js + TypeScript + shadcn/ui
- `corpus/` — synthetic Imperial documents (Phase B+)
- `docs/superpowers/` — specs & implementation plans
```

(Yes, the README hard-codes Phase A. We'll expand it in later phases.)

- [ ] **Step 4: Create `Makefile` skeleton (we'll add targets in later tasks)**

```makefile
PY := .venv/Scripts/python

.PHONY: help backend-venv backend-install backend-migrate backend-seed backend-test frontend-install dev

help:
	@echo "Targets:"
	@echo "  backend-venv      - create .venv (Python 3.11)"
	@echo "  backend-install   - install Python deps into .venv (creates venv if missing)"
	@echo "  backend-migrate   - run alembic upgrade head"
	@echo "  backend-seed      - seed the Imperial tenant and demo users"
	@echo "  backend-test      - run pytest"
	@echo "  frontend-install  - install pnpm deps"
	@echo "  dev               - start backend + frontend (requires postgres+redis up)"

backend-venv:
	cd backend && python -m venv .venv

backend-install:
	cd backend && [ -d .venv ] || python -m venv .venv
	cd backend && $(PY) -m pip install --upgrade pip
	cd backend && $(PY) -m pip install -e ".[dev]"

backend-migrate:
	cd backend && $(PY) -m alembic upgrade head

backend-seed:
	cd backend && $(PY) scripts/seed_users.py

backend-test:
	cd backend && $(PY) -m pytest -v

frontend-install:
	cd frontend && pnpm install

dev:
	@echo "Run these in two terminals (activate the backend venv first):"
	@echo "  cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "  cd frontend && pnpm dev"
```

- [ ] **Step 5: Commit**

```powershell
git add .gitignore README.md Makefile
git commit -m "chore: initialize repo scaffolding"
```

---

## Task 2: Docker Compose (Postgres + pgvector + Redis)

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: holocron-postgres
    environment:
      POSTGRES_USER: holocron
      POSTGRES_PASSWORD: holocron
      POSTGRES_DB: holocron
    ports:
      - "5433:5432"   # host:container — 5433 avoids conflict with any host Postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres-init.sql:/docker-entrypoint-initdb.d/postgres-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U holocron"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: holocron-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  postgres_data:
```

- [ ] **Step 2: Create Postgres init script (creates extensions + the test database)**

Create: `scripts/postgres-init.sql`

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE DATABASE holocron_test;
\connect holocron_test
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

- [ ] **Step 3: Bring services up and verify**

```powershell
docker compose up -d postgres redis
docker compose ps
```

Expected: both containers `running` and `healthy`.

- [ ] **Step 4: Verify pgvector is installed in both databases**

```powershell
docker exec -it holocron-postgres psql -U holocron -d holocron -c "SELECT extname FROM pg_extension;"
docker exec -it holocron-postgres psql -U holocron -d holocron_test -c "SELECT extname FROM pg_extension;"
```

Expected output (both): rows including `vector` and `pg_trgm`.

If you don't see `vector` in `holocron_test`, the init script only runs on a fresh volume. Run `docker compose down -v` then `docker compose up -d postgres` to re-init.

- [ ] **Step 5: Commit**

```powershell
git add docker-compose.yml scripts/postgres-init.sql
git commit -m "chore: add docker-compose with postgres+pgvector and redis"
```

---

## Task 3: Backend `pyproject.toml` + minimal FastAPI app

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "holocron-backend"
version = "0.1.0"
description = "HOLOCRON backend"
requires-python = ">=3.11,<3.12"
dependencies = [
    "fastapi>=0.115,<0.116",
    "uvicorn[standard]>=0.32,<0.33",
    "pydantic>=2.9,<3.0",
    "pydantic-settings>=2.6,<3.0",
    "sqlalchemy[asyncio]>=2.0.36,<2.1",
    "asyncpg>=0.30,<0.31",
    "alembic>=1.14,<1.15",
    "bcrypt>=4.2,<5.0",
    "pyjwt>=2.10,<3.0",
    "python-multipart>=0.0.20,<0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9.0",
    "pytest-asyncio>=0.24,<0.25",
    "httpx>=0.28,<0.29",
    "ruff>=0.8,<0.9",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Create empty `backend/app/__init__.py`** (empty file)

- [ ] **Step 3: Create `backend/app/main.py`** (minimal hello)

```python
from fastapi import FastAPI

app = FastAPI(title="HOLOCRON", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Create `backend/.env.example`**

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://holocron:holocron@localhost:5433/holocron
TEST_DATABASE_URL=postgresql+asyncpg://holocron:holocron@localhost:5433/holocron_test
JWT_SECRET=change-me-in-prod-this-is-only-for-local-dev
JWT_ALGORITHM=HS256
JWT_TTL_HOURS=24
COOKIE_NAME=holocron_session
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
```

- [ ] **Step 5: Copy `.env.example` to `.env`**

```powershell
Copy-Item backend/.env.example backend/.env
```

- [ ] **Step 6: Create the venv and install deps**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

(For Git Bash use `source .venv/Scripts/activate` instead of the `.ps1`.)

Keep this PowerShell window open with the venv activated for the rest of the plan.

- [ ] **Step 7: Verify the server starts**

```powershell
uvicorn app.main:app --port 8000
```

In another terminal:

```powershell
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

Kill the server with Ctrl+C. Return to repo root.

- [ ] **Step 8: Commit**

```powershell
git add backend/pyproject.toml backend/app/__init__.py backend/app/main.py backend/.env.example
git commit -m "feat(backend): add FastAPI skeleton with health endpoint"
```

---

## Task 4: Backend config module (`app/core/config.py`)

**Files:**
- Create: `backend/app/core/__init__.py` (empty)
- Create: `backend/app/core/config.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py` (root fixtures)
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_config.py`**

```python
from app.core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@h/db_test")
    monkeypatch.setenv("JWT_SECRET", "secret-x")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_TTL_HOURS", "12")
    monkeypatch.setenv("COOKIE_NAME", "session")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")

    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h/db"
    assert s.jwt_ttl_hours == 12
    assert s.cookie_secure is False
    assert s.cors_origins == ["http://localhost:3000", "http://localhost:3001"]
```

- [ ] **Step 2: Create empty `backend/tests/__init__.py`** and a minimal `backend/tests/conftest.py`:

```python
# Per-test setup is added in later tasks. Currently empty intentionally.
```

- [ ] **Step 3: Run the test and verify it fails**

```powershell
cd backend
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.config'`.

- [ ] **Step 4: Create empty `backend/app/core/__init__.py`** and implement `backend/app/core/config.py`:

```python
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    database_url: str
    test_database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 24
    cookie_name: str = "holocron_session"
    cookie_secure: bool = False
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

> The `Annotated[..., NoDecode]` wrapper is critical: pydantic-settings v2.x tries to JSON-parse env vars typed as `list[str]` *before* validators run, so a comma-separated value would fail. `NoDecode` defers parsing to our `_split_csv` validator.

- [ ] **Step 5: Run the test, verify pass**

```powershell
pytest tests/test_config.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/core backend/tests/__init__.py backend/tests/conftest.py backend/tests/test_config.py
git commit -m "feat(backend): add Settings via pydantic-settings"
```

---

## Task 5: Backend database module + healthcheck wiring

**Files:**
- Create: `backend/app/core/database.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_database.py`**

```python
import pytest
from sqlalchemy import text

from app.core.database import get_engine


@pytest.mark.asyncio
async def test_engine_can_execute_simple_query():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS one"))
        assert result.scalar_one() == 1
```

- [ ] **Step 2: Run the test and verify it fails**

```powershell
pytest tests/test_database.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement `backend/app/core/database.py`**

```python
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, echo=False, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields an AsyncSession with commit-on-success semantics."""
    Session = get_sessionmaker()
    async with Session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Run the test, verify pass**

Postgres must be running (`docker compose ps` shows `holocron-postgres healthy`).

```powershell
pytest tests/test_database.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Wire the database healthcheck into `app/main.py`**

Replace `backend/app/main.py` with:

```python
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

app = FastAPI(title="HOLOCRON", version="0.1.0")


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
```

- [ ] **Step 6: Smoke-test the live endpoint**

```powershell
uvicorn app.main:app --port 8000
```

In another terminal:

```powershell
curl http://localhost:8000/health
```

Expected: `{"status":"ok","database":"ok"}`. Kill the server.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/core/database.py backend/app/main.py backend/tests/test_database.py
git commit -m "feat(backend): add async SQLAlchemy engine + DB healthcheck"
```

---

## Task 6: Domain enums (`app/domain/enums.py`)

**Files:**
- Create: `backend/app/domain/__init__.py` (empty)
- Create: `backend/app/domain/enums.py`
- Create: `backend/tests/test_enums.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_enums.py`**

```python
import pytest

from app.domain.enums import ClearanceLevel, Department, Role


def test_clearance_level_ordering():
    assert ClearanceLevel.PUBLIC < ClearanceLevel.RESTRICTED
    assert ClearanceLevel.RESTRICTED < ClearanceLevel.SECRET
    assert ClearanceLevel.SECRET < ClearanceLevel.TOP_SECRET


def test_clearance_level_values_are_db_strings():
    assert ClearanceLevel.PUBLIC.value == "public"
    assert ClearanceLevel.TOP_SECRET.value == "top_secret"


@pytest.mark.parametrize(
    "role,expected_max",
    [
        (Role.EMPLOYEE, ClearanceLevel.PUBLIC),
        (Role.MANAGER, ClearanceLevel.RESTRICTED),
        (Role.DIRECTOR, ClearanceLevel.SECRET),
        (Role.EXECUTIVE, ClearanceLevel.TOP_SECRET),
    ],
)
def test_role_max_clearance_mapping(role, expected_max):
    assert role.max_clearance() == expected_max


def test_role_can_see_uses_max_clearance():
    assert Role.MANAGER.can_see(ClearanceLevel.PUBLIC) is True
    assert Role.MANAGER.can_see(ClearanceLevel.RESTRICTED) is True
    assert Role.MANAGER.can_see(ClearanceLevel.SECRET) is False


def test_departments_listed():
    expected = {"hr", "security", "engineering", "fleet_operations", "procurement"}
    assert {d.value for d in Department} == expected
```

- [ ] **Step 2: Run, verify it fails**

```powershell
pytest tests/test_enums.py -v
```

- [ ] **Step 3: Implement `backend/app/domain/enums.py`**

```python
from __future__ import annotations

from enum import Enum
from functools import total_ordering


@total_ordering
class ClearanceLevel(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

    @property
    def _rank(self) -> int:
        return {"public": 0, "restricted": 1, "secret": 2, "top_secret": 3}[self.value]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ClearanceLevel):
            return NotImplemented
        return self._rank < other._rank


class Role(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"

    def max_clearance(self) -> ClearanceLevel:
        return {
            Role.EMPLOYEE: ClearanceLevel.PUBLIC,
            Role.MANAGER: ClearanceLevel.RESTRICTED,
            Role.DIRECTOR: ClearanceLevel.SECRET,
            Role.EXECUTIVE: ClearanceLevel.TOP_SECRET,
        }[self]

    def can_see(self, classification: ClearanceLevel) -> bool:
        return classification <= self.max_clearance()


class Department(str, Enum):
    HR = "hr"
    SECURITY = "security"
    ENGINEERING = "engineering"
    FLEET_OPERATIONS = "fleet_operations"
    PROCUREMENT = "procurement"
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_enums.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domain backend/tests/test_enums.py
git commit -m "feat(backend): add domain enums (ClearanceLevel, Role, Department)"
```

---

## Task 7: SQLAlchemy ORM models (Tenant, User) + base

> We intentionally only model the tables Phase A *exercises*. The Phase A migration (Task 8) creates **all** Phase A–D tables as raw SQL so we don't introduce unused ORM models prematurely. Models for `Document`, `Chunk`, `AuditEvent` arrive in their respective phases.

**Files:**
- Create: `backend/app/domain/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_models.py`**

```python
import uuid

from app.domain.enums import Role
from app.domain.models import Tenant, User


def test_tenant_has_expected_columns():
    t = Tenant(name="Galactic Empire", role_label_map={"employee": "Imperial Employee"})
    assert t.name == "Galactic Empire"
    assert t.role_label_map["employee"] == "Imperial Employee"


def test_user_default_departments_is_empty_list():
    u = User(
        tenant_id=uuid.uuid4(),
        username="ts-001",
        password_hash="x",
        role=Role.EMPLOYEE.value,
        max_clearance="public",
    )
    assert u.departments == []
```

- [ ] **Step 2: Run, verify it fails**

```powershell
pytest tests/test_models.py -v
```

- [ ] **Step 3: Implement `backend/app/domain/models.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, TIMESTAMP, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role_label_map: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    max_clearance: Mapped[str] = mapped_column(String(32), nullable=False)
    departments: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
```

Note: `role` and `max_clearance` are stored as `String` columns even though the database uses a Postgres ENUM for `classification_level` on the `chunks` and `documents` tables (added in the migration). For `users.max_clearance`, we use the same enum (referenced by string) — the DB-level CHECK is provided by the enum type defined in the migration. We avoid mapping the SQLAlchemy `Enum` type here to keep model imports framework-light for Phase A; we'll revisit when Phase B introduces `documents`/`chunks` ORM models.

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_models.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domain/models.py backend/tests/test_models.py
git commit -m "feat(backend): add Tenant and User ORM models"
```

---

## Task 8: Alembic init + initial migration (all Phase A–D tables)

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_phase_a_initial.py`

- [ ] **Step 1: Initialize Alembic structure**

```powershell
cd backend
alembic init -t async alembic
```

This generates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Edit `backend/alembic.ini`**

Replace the `sqlalchemy.url = ...` line near the top with:

```ini
sqlalchemy.url =
```

(Leave it blank — we set the URL programmatically in `env.py`.)

- [ ] **Step 3: Replace `backend/alembic/env.py` entirely with:**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.domain.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    import os
    return os.environ.get("ALEMBIC_DATABASE_URL", get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {}) or {}
    cfg["sqlalchemy.url"] = _db_url()
    connectable = async_engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Delete the generated stub in `backend/alembic/versions/` (any `*.py` file Alembic produced)** — we'll write our own initial migration.

- [ ] **Step 5: Create `backend/alembic/versions/0001_phase_a_initial.py`**

This migration creates every Phase A–D table per spec §5 in raw SQL form (we won't generate it from autogenerate because we don't yet have ORM models for chunks/documents/audit_events).

```python
"""phase A initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")  # for gen_random_uuid()

    op.execute(
        """
        CREATE TABLE tenants (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            role_label_map  JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE TYPE clearance_level AS ENUM ('public','restricted','secret','top_secret');")

    op.execute(
        """
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            username        TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
            role            TEXT NOT NULL CHECK (role IN ('employee','manager','director','executive')),
            max_clearance   clearance_level NOT NULL,
            departments     TEXT[] NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, username)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE documents (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            title           TEXT NOT NULL,
            source_uri      TEXT,
            classification  clearance_level NOT NULL,
            department      TEXT NOT NULL,
            version         TEXT NOT NULL,
            effective_date  DATE NOT NULL,
            lineage_id      UUID NOT NULL,
            uploaded_by     UUID REFERENCES users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE chunks (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            ordinal         INT NOT NULL,
            text            TEXT NOT NULL,
            text_tsv        TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
            embedding       VECTOR(768),
            classification  clearance_level NOT NULL,
            department      TEXT NOT NULL,
            effective_date  DATE NOT NULL,
            lineage_id      UUID NOT NULL,
            entities        TEXT[] NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);"
    )
    op.execute("CREATE INDEX chunks_text_tsv_gin ON chunks USING gin (text_tsv);")
    op.execute(
        "CREATE INDEX chunks_tenant_cls_dept ON chunks (tenant_id, classification, department);"
    )
    op.execute("CREATE INDEX chunks_lineage ON chunks (lineage_id);")

    op.execute(
        """
        CREATE TABLE audit_events (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL,
            user_id         UUID NOT NULL,
            event_type      TEXT NOT NULL,
            query_text      TEXT,
            retrieved_ids   UUID[],
            withheld_ids    UUID[],
            refusal_ref     TEXT,
            response_text   TEXT,
            conflicts_found JSONB,
            latency_ms      INT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX audit_user_time ON audit_events (tenant_id, user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events;")
    op.execute("DROP TABLE IF EXISTS chunks;")
    op.execute("DROP TABLE IF EXISTS documents;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP TYPE  IF EXISTS clearance_level;")
    op.execute("DROP TABLE IF EXISTS tenants;")
```

- [ ] **Step 6: Run the migration**

```powershell
alembic upgrade head
```

Expected: `INFO ... Running upgrade -> 0001, phase A initial schema`.

- [ ] **Step 7: Verify schema**

```powershell
docker exec -it holocron-postgres psql -U holocron -d holocron -c "\dt"
```

Expected: a list including `audit_events`, `chunks`, `documents`, `tenants`, `users`, `alembic_version`.

```powershell
docker exec -it holocron-postgres psql -U holocron -d holocron -c "\d chunks"
```

Expected: shows the `text_tsv` generated column, the `embedding vector(768)` column, and the four indexes.

- [ ] **Step 8: Run downgrade-then-upgrade round-trip to prove migrations are reversible**

```powershell
alembic downgrade base
alembic upgrade head
```

Both should succeed.

- [ ] **Step 9: Commit**

```powershell
git add backend/alembic.ini backend/alembic
git commit -m "feat(backend): add alembic + initial Phase A migration (all tables)"
```

---

## Task 9: Password hashing module (`app/core/security.py` — Part 1)

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/tests/test_security.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_security.py`**

```python
import pytest

from app.core.security import hash_password, verify_password


def test_hash_password_returns_different_hashes_for_same_input():
    h1 = hash_password("correct horse battery staple")
    h2 = hash_password("correct horse battery staple")
    assert h1 != h2  # bcrypt salts


def test_verify_password_correct():
    h = hash_password("secret-123")
    assert verify_password("secret-123", h) is True


def test_verify_password_wrong():
    h = hash_password("secret-123")
    assert verify_password("secret-456", h) is False


def test_verify_password_with_malformed_hash_returns_false():
    assert verify_password("x", "not-a-bcrypt-hash") is False
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_security.py -v
```

- [ ] **Step 3: Implement password helpers in `backend/app/core/security.py`**

```python
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_security.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat(backend): add bcrypt password hashing helpers"
```

---

## Task 10: JWT helpers (extend `app/core/security.py`)

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/tests/test_security.py`

- [ ] **Step 1: Append failing JWT tests to `backend/tests/test_security.py`**

```python
import time
import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
    decode_session_token,
    encode_session_token,
)


def test_encode_decode_roundtrip():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=60)
    claims = decode_session_token(token)
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id


def test_expired_token_rejected():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=-1)
    with pytest.raises(InvalidTokenError):
        decode_session_token(token)


def test_tampered_token_rejected():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=60)
    # flip a character
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(InvalidTokenError):
        decode_session_token(tampered)
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_security.py -v
```

- [ ] **Step 3: Append JWT helpers to `backend/app/core/security.py`**

```python
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class SessionClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


def encode_session_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID, ttl_seconds: int | None = None) -> str:
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.jwt_ttl_hours * 3600
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_session_token(token: str) -> SessionClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e
    try:
        return SessionClaims(user_id=uuid.UUID(payload["sub"]), tenant_id=uuid.UUID(payload["tid"]))
    except (KeyError, ValueError) as e:
        raise InvalidTokenError("malformed claims") from e
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_security.py -v
```

Expected: all 7 tests pass (4 password + 3 JWT).

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/security.py backend/tests/test_security.py
git commit -m "feat(backend): add JWT session-token helpers"
```

---

## Task 11: DB-backed test fixtures + UserRepository

**Files:**
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/repositories/__init__.py` (empty)
- Create: `backend/app/repositories/user_repository.py`
- Create: `backend/tests/test_user_repository.py`

- [ ] **Step 1: Replace `backend/tests/conftest.py` with full DB fixtures**

```python
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.domain.models import Base, Tenant

# Force the engine to use the TEST database for the duration of the test session.
os.environ.setdefault("DATABASE_URL", get_settings().test_database_url)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    settings = get_settings()
    engine = create_async_engine(settings.test_database_url, pool_pre_ping=True)
    # Reset schema once per session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """Per-test session with rollback isolation."""
    connection = await test_engine.connect()
    transaction = await connection.begin()
    Session = async_sessionmaker(bind=connection, expire_on_commit=False)
    async with Session() as session:
        try:
            yield session
        finally:
            await session.close()
    await transaction.rollback()
    await connection.close()


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
```

Note: this conftest uses `Base.metadata.create_all` (not Alembic) to set up the test schema. That gives us `tenants` and `users` for Phase A tests. The Alembic migration is still verified by Task 8's round-trip step. We'll add a CI-style migration test in Phase B when more tables matter.

- [ ] **Step 2: Write failing tests `backend/tests/test_user_repository.py`**

```python
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
```

- [ ] **Step 3: Run, verify fail**

```powershell
pytest tests/test_user_repository.py -v
```

- [ ] **Step 4: Implement `backend/app/repositories/user_repository.py`**

```python
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
```

> **Boundary note:** every read in `UserRepository` is tenant-scoped by parameter — there is no `get_by_id(user_id)` without `tenant_id`. This is the Phase A version of the "RBAC at the data layer" discipline we'll extend in Phase B to chunks.

Also create empty `backend/app/repositories/__init__.py`.

- [ ] **Step 5: Run, verify pass**

```powershell
pytest tests/test_user_repository.py -v
```

- [ ] **Step 6: Commit**

```powershell
git add backend/app/repositories backend/tests/conftest.py backend/tests/test_user_repository.py
git commit -m "feat(backend): add UserRepository with tenant-scoped reads"
```

---

## Task 12: Auth API — Pydantic schemas + login endpoint

**Files:**
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/schemas.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_auth_api.py`**

```python
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import User
from app.main import app


@pytest_asyncio.fixture
async def client(test_engine, db_session):
    # Override get_session so the request uses the same connection/transaction as db_session.
    from app.core.database import get_session

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_employee(db_session, empire_tenant):
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="ts-001",
        password_hash=hash_password("imperial-march"),
        role=Role.EMPLOYEE.value,
        max_clearance=ClearanceLevel.PUBLIC.value,
        departments=["security"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_login_success_sets_cookie_and_returns_user(client, empire_tenant, seeded_employee):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "ts-001"
    assert body["role"] == "employee"
    assert body["max_clearance"] == "public"
    assert body["departments"] == ["security"]
    assert body["tenant"]["name"] == "Galactic Empire"
    assert body["tenant"]["role_label"] == "Imperial Employee"
    # Cookie set
    assert "holocron_session" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client, empire_tenant, seeded_employee):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client, empire_tenant):
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ghost", "password": "x"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_auth_api.py -v
```

- [ ] **Step 3: Create `backend/app/api/schemas.py`**

```python
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
```

- [ ] **Step 4: Create `backend/app/api/auth.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoginRequest, TenantSummary, UserSummary
from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import encode_session_token, verify_password
from app.domain.models import Tenant
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_user_summary(user, tenant: Tenant) -> UserSummary:
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
```

- [ ] **Step 5: Register the router and add CORS in `backend/app/main.py`** (replace contents)

```python
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.core.database import get_session

settings = get_settings()

app = FastAPI(title="HOLOCRON", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(auth_router)
```

- [ ] **Step 6: Run, verify pass**

```powershell
pytest tests/test_auth_api.py -v
```

- [ ] **Step 7: Commit**

```powershell
git add backend/app/api backend/app/main.py backend/tests/test_auth_api.py
git commit -m "feat(backend): add /auth/login with cookie session"
```

---

## Task 13: Auth dependency + `/auth/me` + `/auth/logout`

**Files:**
- Create: `backend/app/api/deps.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Append failing tests to `backend/tests/test_auth_api.py`**

```python
@pytest.mark.asyncio
async def test_me_returns_current_user_when_authed(client, empire_tenant, seeded_employee):
    login = await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    assert login.status_code == 200

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "ts-001"


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_subsequent_me_is_401(client, empire_tenant, seeded_employee):
    await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": "ts-001", "password": "imperial-march"},
    )
    logout = await client.delete("/auth/session")
    assert logout.status_code == 204

    me = await client.get("/auth/me")
    assert me.status_code == 401
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_auth_api.py -v
```

- [ ] **Step 3: Create `backend/app/api/deps.py`**

```python
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
```

- [ ] **Step 4: Append `/auth/me` and `/auth/session` (DELETE) to `backend/app/api/auth.py`**

Add the imports at the top:

```python
from app.api.deps import get_current_user
from app.domain.models import User
```

Append at the bottom:

```python
@router.get("/me", response_model=UserSummary)
async def me(current: tuple[User, Tenant] = Depends(get_current_user)) -> UserSummary:
    user, tenant = current
    return _build_user_summary(user, tenant)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=get_settings().cookie_name, path="/")
```

- [ ] **Step 5: Run, verify pass**

```powershell
pytest tests/test_auth_api.py -v
```

Expected: 6 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/api/deps.py backend/app/api/auth.py backend/tests/test_auth_api.py
git commit -m "feat(backend): add /auth/me and /auth/session DELETE"
```

---

## Task 14: Tenant-context dependency

**Files:**
- Create: `backend/app/core/tenant.py`
- Create: `backend/tests/test_tenant_context.py`

- [ ] **Step 1: Write failing tests `backend/tests/test_tenant_context.py`**

```python
import uuid

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
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
    from app.core.security import encode_session_token

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
```

- [ ] **Step 2: Run, verify fail**

```powershell
pytest tests/test_tenant_context.py -v
```

- [ ] **Step 3: Implement `backend/app/core/tenant.py`**

```python
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
```

- [ ] **Step 4: Run, verify pass**

```powershell
pytest tests/test_tenant_context.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core/tenant.py backend/tests/test_tenant_context.py
git commit -m "feat(backend): add TenantContext dependency"
```

---

## Task 15: Seed script (Imperial tenant + demo users)

**Files:**
- Create: `backend/scripts/__init__.py` (empty)
- Create: `backend/scripts/seed_users.py`

- [ ] **Step 1: Implement `backend/scripts/seed_users.py`**

```python
"""Seed the Galactic Empire tenant and one demo user per (role x department) cell.

Run via `make backend-seed` (or `python scripts/seed_users.py` from `backend/`).
Idempotent: safe to re-run.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import get_sessionmaker
from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Department, Role
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
    # Two users per role across two departments (8 users total)
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
```

- [ ] **Step 2: Run the seed script**

```powershell
cd backend
python scripts/seed_users.py
```

Expected: prints the tenant id, default password, and 8 user lines.

- [ ] **Step 3: Re-run to verify idempotence**

```powershell
python scripts/seed_users.py
```

Expected: same output, no errors.

- [ ] **Step 4: Verify in the database**

```powershell
docker exec -it holocron-postgres psql -U holocron -d holocron -c "SELECT username, role, max_clearance, departments FROM users ORDER BY role, username;"
```

Expected: 8 rows.

- [ ] **Step 5: Smoke-test login via curl**

Start the server:

```powershell
uvicorn app.main:app --port 8000
```

In another terminal, fetch the tenant id:

```powershell
$tid = (docker exec -it holocron-postgres psql -U holocron -d holocron -t -A -c "SELECT id FROM tenants WHERE name='Galactic Empire';").Trim()
curl -i -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"tenant_id\": \"$tid\", \"username\": \"employee.security\", \"password\": \"imperial-march\"}"
```

Expected: HTTP 200, body includes `"role_label":"Imperial Employee"`, response sets `Set-Cookie: holocron_session=...`.

Kill the server.

- [ ] **Step 6: Commit**

```powershell
git add backend/scripts
git commit -m "feat(backend): add seed script for Imperial tenant + demo users"
```

---

## Task 16: Frontend scaffold (Next.js + Tailwind + shadcn)

**Files:**
- Many under `frontend/`

- [ ] **Step 1: Scaffold Next.js**

From the repo root:

```powershell
pnpm create next-app@15.0.0 frontend --typescript --tailwind --app --src-dir false --eslint --import-alias "@/*" --use-pnpm --turbopack false --no-git
```

If the CLI prompts interactively for any unspecified flags, accept defaults that match the above.

- [ ] **Step 2: Initialize shadcn/ui**

```powershell
cd frontend
pnpm dlx shadcn@latest init -d
```

When asked: style "default", base color "slate", CSS variables "yes".

This creates `components.json`, `lib/utils.ts`, and updates `tailwind.config.ts` + `app/globals.css`.

- [ ] **Step 3: Add the shadcn components we need**

```powershell
pnpm dlx shadcn@latest add button input label card badge
```

- [ ] **Step 4: Create `frontend/.env.local.example`**

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_TENANT_ID=
```

Copy to `.env.local`:

```powershell
Copy-Item .env.local.example .env.local
```

After Task 15 you can fill `NEXT_PUBLIC_DEFAULT_TENANT_ID` with the printed tenant id so the login form pre-fills it.

- [ ] **Step 5: Smoke-test dev server**

```powershell
pnpm dev
```

Open <http://localhost:3000> in a browser. Expected: the default Next.js welcome page renders. Stop the server.

- [ ] **Step 6: Commit**

```powershell
cd ..
git add frontend
git commit -m "chore(frontend): scaffold Next.js + Tailwind + shadcn"
```

---

## Task 17: Frontend API client (`lib/api.ts`, `lib/types.ts`)

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create `frontend/lib/types.ts`**

```typescript
export type ClearanceLevel = 'public' | 'restricted' | 'secret' | 'top_secret';

export type Role = 'employee' | 'manager' | 'director' | 'executive';

export interface TenantSummary {
  id: string;
  name: string;
  role_label: string;
}

export interface UserSummary {
  id: string;
  username: string;
  role: Role;
  max_clearance: ClearanceLevel;
  departments: string[];
  tenant: TenantSummary;
}

export interface ApiError {
  status: number;
  detail: string;
}
```

- [ ] **Step 2: Create `frontend/lib/api.ts`**

```typescript
import type { ApiError, UserSummary } from './types';

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // ignore JSON parse errors on error responses
    }
    const err: ApiError = { status: res.status, detail };
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (tenant_id: string, username: string, password: string) =>
    request<UserSummary>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ tenant_id, username, password }),
    }),
  me: () => request<UserSummary>('/auth/me'),
  logout: () => request<void>('/auth/session', { method: 'DELETE' }),
};
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/lib
git commit -m "feat(frontend): add API client with cookie credentials"
```

---

## Task 18: Login page (`/login`)

**Files:**
- Create: `frontend/app/login/page.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Replace `frontend/app/page.tsx`** with a redirect to `/me`:

```tsx
import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/me');
}
```

- [ ] **Step 2: Create `frontend/app/login/page.tsx`**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [tenantId, setTenantId] = useState(process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.login(tenantId.trim(), username.trim(), password);
      router.push('/me');
    } catch (err) {
      const msg = (err as { detail?: string })?.detail ?? 'login failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>HOLOCRON</CardTitle>
          <CardDescription>Imperial Knowledge Assistant — sign in</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="tenant">Tenant ID</Label>
              <Input
                id="tenant"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                placeholder="UUID of the Galactic Empire tenant"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. employee.security"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 3: Manual smoke test**

In two terminals:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
pnpm dev
```

Open <http://localhost:3000/login>, paste the Galactic Empire tenant id from the seed output, log in as `employee.security` / `imperial-march`. The form should redirect to `/me` (which 404s for now — that's the next task). Stop both servers.

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/page.tsx frontend/app/login
git commit -m "feat(frontend): add /login page"
```

---

## Task 19: `/me` page + `ClearanceBadge` component

**Files:**
- Create: `frontend/components/ClearanceBadge.tsx`
- Create: `frontend/app/me/page.tsx`

- [ ] **Step 1: Create `frontend/components/ClearanceBadge.tsx`**

```tsx
import { Badge } from '@/components/ui/badge';
import type { ClearanceLevel } from '@/lib/types';

const COLORS: Record<ClearanceLevel, string> = {
  public: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  restricted: 'bg-amber-100 text-amber-800 border-amber-300',
  secret: 'bg-orange-100 text-orange-900 border-orange-300',
  top_secret: 'bg-red-100 text-red-900 border-red-300',
};

const LABELS: Record<ClearanceLevel, string> = {
  public: 'Public',
  restricted: 'Restricted',
  secret: 'Secret',
  top_secret: 'Top Secret',
};

export function ClearanceBadge({ level }: { level: ClearanceLevel }) {
  return (
    <Badge variant="outline" className={`border ${COLORS[level]} font-medium`}>
      {LABELS[level]}
    </Badge>
  );
}
```

- [ ] **Step 2: Create `frontend/app/me/page.tsx`**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ClearanceBadge } from '@/components/ClearanceBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import type { UserSummary } from '@/lib/types';

export default function MePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => router.replace('/login'))
      .finally(() => setLoading(false));
  }, [router]);

  async function onLogout() {
    await api.logout();
    router.replace('/login');
  }

  if (loading) return <main className="p-8">Loading…</main>;
  if (!user) return null;

  return (
    <main className="mx-auto max-w-2xl p-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{user.tenant.role_label}: {user.username}</CardTitle>
          <CardDescription>{user.tenant.name}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">Max clearance:</span>
            <ClearanceBadge level={user.max_clearance} />
          </div>
          <div>
            <p className="text-sm text-slate-500">Departments</p>
            <p className="font-medium">{user.departments.join(', ') || '—'}</p>
          </div>
          <Button variant="outline" onClick={onLogout}>Sign out</Button>
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 3: Manual smoke test (the Phase A end-of-phase demo)**

Backend + frontend running as in Task 18. Open <http://localhost:3000/login>.

1. Log in as `employee.security` / `imperial-march`. `/me` should show `Imperial Employee: employee.security`, max clearance badge **Public** (emerald), departments `security`.
2. Click "Sign out" — you should land back at `/login`.
3. Log in as `executive.fleet`. `/me` should show `Imperial Executive`, badge **Top Secret** (red), departments `fleet_operations, security`.
4. Visit `/me` in an incognito window — you should be redirected to `/login`.

- [ ] **Step 4: Commit**

```powershell
git add frontend/components/ClearanceBadge.tsx frontend/app/me
git commit -m "feat(frontend): add /me page with clearance badge"
```

---

## Task 20: Backend + frontend Dockerfiles + docker-compose wiring

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `backend/.dockerignore`**

```
.venv
__pycache__
.pytest_cache
.ruff_cache
.mypy_cache
tests
.env
```

- [ ] **Step 3: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
COPY --from=builder /app/package.json /app/pnpm-lock.yaml ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["pnpm", "start"]
```

- [ ] **Step 4: Create `frontend/.dockerignore`**

```
node_modules
.next
.turbo
.env.local
```

- [ ] **Step 5: Extend `docker-compose.yml`** (add `backend` and `frontend` services; keep `postgres`/`redis` unchanged)

Replace the file with:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: holocron-postgres
    environment:
      POSTGRES_USER: holocron
      POSTGRES_PASSWORD: holocron
      POSTGRES_DB: holocron
    ports:
      - "5433:5432"   # host:container — 5433 avoids conflict with any host Postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres-init.sql:/docker-entrypoint-initdb.d/postgres-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U holocron"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: holocron-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build: ./backend
    container_name: holocron-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://holocron:holocron@postgres:5432/holocron
      TEST_DATABASE_URL: postgresql+asyncpg://holocron:holocron@postgres:5432/holocron_test
      JWT_SECRET: change-me-in-prod-this-is-only-for-local-dev
      JWT_ALGORITHM: HS256
      JWT_TTL_HOURS: "24"
      COOKIE_NAME: holocron_session
      COOKIE_SECURE: "false"
      CORS_ORIGINS: http://localhost:3000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    container_name: holocron-frontend
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    depends_on:
      - backend
    ports:
      - "3000:3000"

volumes:
  postgres_data:
```

- [ ] **Step 6: Full-stack build and run**

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps
```

Expected: all four containers `running`. The backend may exit and restart if migrations haven't run — that's fine; we run them next.

- [ ] **Step 7: Run migrations and seed inside the backend container**

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_users.py
```

- [ ] **Step 8: End-to-end browser test**

Open <http://localhost:3000>. You should land on `/me`, get redirected to `/login`. Paste the seeded tenant id (visible in the previous step's output). Log in as `executive.fleet`. `/me` should render with the **Top Secret** badge. Sign out. Log in as `employee.security`. Badge should be **Public**.

- [ ] **Step 9: Commit**

```powershell
git add backend/Dockerfile backend/.dockerignore frontend/Dockerfile frontend/.dockerignore docker-compose.yml
git commit -m "chore: dockerize backend and frontend; wire compose"
```

---

## Task 21: README quickstart polish + Phase A DoD verification

**Files:**
- Modify: `README.md`
- Create: `docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md`

- [ ] **Step 1: Replace `README.md` Quickstart section so it matches the actual flow**

```markdown
# HOLOCRON

Classification-aware enterprise RAG over a synthetic Galactic Empire corpus.
See `docs/superpowers/specs/2026-06-27-holocron-design.md` for the design.

## Quickstart (Phase A — Foundation)

Prereqs: Docker Desktop running, Python 3.11 (we use pip + venv), `pnpm` for any local frontend work.

### One-command (containers)

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_users.py
# Note the tenant id printed by the seed command.
```

Open <http://localhost:3000>, log in with the tenant id and one of the seeded accounts.

### Local dev (hot reload)

```bash
docker compose up -d postgres redis
make backend-install      # creates .venv and installs deps
make backend-migrate
make backend-seed         # copy the tenant id from the output
cd frontend && pnpm install && cd ..

# Terminal A (activate the venv first):
cd backend
# PowerShell:  .\.venv\Scripts\Activate.ps1
# Git Bash:    source .venv/Scripts/activate
uvicorn app.main:app --reload --port 8000

# Terminal B:
cd frontend && pnpm dev
```

### Seeded demo accounts

All passwords: `imperial-march`.

| Username                | Role      | Departments               | Badge      |
|-------------------------|-----------|---------------------------|------------|
| employee.security       | Employee  | security                  | Public     |
| employee.engineering    | Employee  | engineering               | Public     |
| manager.hr              | Manager   | hr                        | Restricted |
| manager.engineering     | Manager   | engineering               | Restricted |
| director.engineering    | Director  | engineering               | Secret     |
| director.security       | Director  | security                  | Secret     |
| executive.fleet         | Executive | fleet_operations,security | Top Secret |
| executive.procurement   | Executive | procurement,hr            | Top Secret |

### Tests

```bash
make backend-test
```

## Layout

- `backend/` — FastAPI + SQLAlchemy + Alembic
- `frontend/` — Next.js + TypeScript + shadcn/ui
- `corpus/` — synthetic Imperial documents (Phase B+)
- `docs/superpowers/` — specs & implementation plans
```

- [ ] **Step 2: Run the full test suite**

```powershell
make backend-test
```

Expected: all tests pass.

- [ ] **Step 3: Phase A Definition of Done — verify each criterion manually and tick off**

Create `docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md`:

```markdown
# Phase A — Foundation: Completion Record

Date verified: <fill in>

## End-of-phase demo checklist

- [ ] `docker compose down -v && docker compose up -d --build` succeeds on a clean machine in < 10 minutes.
- [ ] `docker compose exec backend alembic upgrade head` completes without error.
- [ ] `docker compose exec backend python scripts/seed_users.py` seeds the Imperial tenant and 8 demo users.
- [ ] `make backend-test` is fully green.
- [ ] Login as `employee.security` renders `/me` with badge **Public** and department `security`.
- [ ] Login as `executive.fleet` renders `/me` with badge **Top Secret** and departments `fleet_operations, security`.
- [ ] `tenants.role_label_map` produces the per-tenant label "Imperial Employee" / "Imperial Executive" in the UI (not the bare `employee` / `executive` strings).
- [ ] Sign-out returns the user to `/login` and a subsequent visit to `/me` redirects to `/login` again.

## Spec coverage

- §10.1 deliverables 1–8: all implemented (see plan tasks).
- §5 schema: full Phase A–D schema applied via migration 0001 (verified by downgrade/upgrade round-trip in Task 8).
- Multi-tenant readiness: every Phase A table carries `tenant_id`; all `UserRepository` reads are tenant-parameterized.
- Tenant-agnostic roles + per-tenant labels: `users.role` stores `employee|manager|director|executive`; `tenants.role_label_map` provides display labels.

## Known follow-ups for Phase B

- Add `documents`, `chunks`, `audit_events` ORM models alongside the ingestion service.
- Wire structlog (deferred to Phase D).
- Add CORS origins for production deploy (Phase 3).
```

- [ ] **Step 4: Tick the boxes after manual verification**

Run the demo flow. Mark each unchecked box as `[x]`. Fill in the date.

- [ ] **Step 5: Commit**

```powershell
git add README.md docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md
git commit -m "docs: complete Phase A foundation with verified DoD checklist"
```

---

## Self-review notes (already applied)

- **Spec coverage:** Every §10.1 deliverable maps to a task — scaffolding (Tasks 1-3), migrations & schema (Task 8), `core/` config/security/tenant (Tasks 4, 5, 9, 10, 14), `domain/` entities (Tasks 6, 7), auth API (Tasks 12, 13), seeded users (Task 15), `/login` & `/me` frontend (Tasks 18, 19), end-of-phase demo (Tasks 20, 21).
- **Multi-tenancy readiness:** `users.role` is the generic ladder; `tenants.role_label_map` carries display labels; every repo read is tenant-parameterized.
- **No placeholders:** Every code block is complete and runnable; every command has an expected outcome.
- **Type / name consistency:** `UserSummary` shape matches between `app/api/schemas.py` and `frontend/lib/types.ts`. The cookie name `holocron_session` matches between `Settings.cookie_name` default, the test fixture override, the Dockerfile env, and the docker-compose env. JWT claim names (`sub`, `tid`) are produced by `encode_session_token` and consumed by `decode_session_token`.
- **TDD discipline:** Every backend behavior change has a failing test before implementation. Frontend uses manual verification in Phase A; automated frontend tests come in Phase B with Playwright if needed.
