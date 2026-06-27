# HOLOCRON — Claude session handoff

> **For Claude:** This file is loaded automatically. Read it first, then read the spec, the latest plan, and the latest completion record before doing anything.

## What this project is

**HOLOCRON** is a portfolio-grade enterprise RAG system over a synthetic Galactic Empire corpus. Two flagship capabilities are the demo: **classification-aware retrieval** (clearance-filtered hybrid search + honest refusal) and **knowledge-conflict detection** (LLM-as-judge flags contradictions side-by-side). Built by a senior full-stack dev (`.NET`/Python/PostgreSQL background) transitioning into AI Engineering.

## Source-of-truth documents (read in this order)

1. **Design spec:** [docs/superpowers/specs/2026-06-27-holocron-design.md](docs/superpowers/specs/2026-06-27-holocron-design.md) — full product, architecture, data model, MVP phasing
2. **Phase A plan:** [docs/superpowers/plans/2026-06-27-phase-a-foundation.md](docs/superpowers/plans/2026-06-27-phase-a-foundation.md) — completed
3. **Phase A completion record:** [docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md](docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md) — includes plan deviations and what worked vs. didn't
4. **Original brief:** [initial_idea.txt](initial_idea.txt) — untracked; the user's starting prompt

## Phase status

- **Phase A — Foundation:** ✅ done (auth, RBAC scaffolding, schema, seeded users, /login + /me UI)
- **Phase B — Ingestion + Classification-Aware Retrieval:** ⏭ next — see spec §10.2
- **Phase C — Conflict Detection + Frontend:** pending — see spec §10.3
- **Phase D — Eval + Audit + Polish:** pending — see spec §10.4

When starting Phase B, invoke the **superpowers:writing-plans** skill against §10.2 deliverables.

## Tech stack as actually built (not what the spec listed)

| Concern | Choice | Notes |
|---|---|---|
| Python | **3.11** (not 3.12) | User runs 3.11 locally. Don't use PEP 695 / `@override` / 3.12-only syntax. |
| Python deps | **pip + venv** (not `uv`) | `uv` was not installed; plan was switched. `pyproject.toml` uses setuptools + `[project.optional-dependencies].dev`. |
| Backend | FastAPI 0.115, async SQLAlchemy 2.x, asyncpg, Alembic | pydantic v2 + pydantic-settings |
| Auth | JWT in HttpOnly cookie (PyJWT), bcrypt hashes | Cookie name: `holocron_session` |
| Postgres | pgvector/pgvector:pg16 via Docker | **Host port 5433** (not 5432) — avoids conflict with user's existing host Postgres install |
| Redis | redis:7-alpine via Docker | Not wired yet; for arq jobs in Phase B+ |
| Frontend | Next.js 15.0.0, React 19 RC, TypeScript, Tailwind v3, shadcn/ui | App Router, no `src/` dir |
| Frontend pkg mgr | pnpm 11 — **one-time `pnpm approve-builds --all`** required after fresh install (sharp + unrs-resolver) |
| Container base | `python:3.11-slim` backend, `node:22-alpine` frontend | |

## Critical conventions

- **Roles are tenant-agnostic, labels are per-tenant.** `users.role` stores `'employee' | 'manager' | 'director' | 'executive'`. Display labels live in `tenants.role_label_map` (e.g., `{"employee": "Imperial Employee"}`). Never hard-code "Imperial X" in code or queries — read from the tenant.
- **Multi-tenant from day one.** Every table has `tenant_id`. Every repository read takes a `tenant_id` parameter — no exceptions. `UserRepository` enforces this; do the same for `DocumentRepository`, `ChunkRepository`, `AuditRepository` when adding them.
- **Classification levels are TEXT + CHECK, not Postgres ENUM.** Spec §5 originally specified an ENUM; the migration was switched to `TEXT NOT NULL CHECK (col IN (...))` because asyncpg requires explicit casts for ENUM↔`String` and it created friction. Validation is identical.
- **Per-test DB fixture recreates schema each test** (`tests/conftest.py`). Slow (~50ms/test) but bulletproof against pytest-asyncio loop-scope issues on Windows + asyncpg. Don't try to optimize to session-scope without testing thoroughly.
- **`User.__init__` overrides `departments` default to `[]`.** SQLAlchemy 2.x `Mapped`'s `default=list` only applies on DB insert, not on Python construction. If you add another array column to a model, do the same.
- **`Settings.cors_origins` uses `Annotated[..., NoDecode]`.** Without this, pydantic-settings JSON-parses comma-separated env vars before validators run and fails.

## Local dev quickstart

```powershell
# 1. Start services (assumes Docker Desktop running)
docker compose up -d postgres redis

# 2. Backend (one-time)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python scripts/seed_users.py   # prints tenant id + seeded usernames

# 3. Frontend (one-time)
cd ..\frontend
pnpm install
pnpm approve-builds --all      # one-time; otherwise pnpm dev fails preflight
# Edit .env.local: NEXT_PUBLIC_DEFAULT_TENANT_ID=<tenant id from seed output>

# 4. Run (two terminals)
# Terminal A:
cd backend && .\.venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8000
# Terminal B:
cd frontend && pnpm dev
```

Open <http://localhost:3000>, log in with `executive.fleet` / `imperial-march`.

## Tests

```powershell
cd backend && .\.venv\Scripts\Activate.ps1 && python -m pytest -v
```

Currently: **30 tests, all passing**. Phase B will add more.

## Demo accounts (all password: `imperial-march`)

| Username                | Tier      | Departments               |
|-------------------------|-----------|---------------------------|
| employee.security       | Employee  | security                  |
| employee.engineering    | Employee  | engineering               |
| manager.hr              | Manager   | hr                        |
| manager.engineering     | Manager   | engineering               |
| director.engineering    | Director  | engineering               |
| director.security       | Director  | security                  |
| executive.fleet         | Executive | fleet_operations,security |
| executive.procurement   | Executive | procurement,hr            |

## Known follow-ups

- **Frontend Docker build** fails on this host with `pnpm install --frozen-lockfile` hitting transient npm registry errors from inside the container — Docker Desktop networking quirk, not a Dockerfile issue. Backend Docker image builds fine. Retry when the network cooperates.
- `corpus/` directory doesn't exist yet — Phase B creates it with ~15-20 synthetic Imperial documents.
- structlog, audit log, Ragas, Langfuse all deferred to later phases per spec §2 "Non-Goals (MVP)".

## How to collaborate with this user

- They picked the 4-phase MVP split deliberately — each phase ends at a demoable milestone. Don't merge phases or skip the end-of-phase demo.
- They lean recommendation-first: present 2-3 options with a clear recommended pick rather than asking open-ended.
- They want enterprise-corporate framing, not military/Star Wars-heavy framing. "Imperial Employee/Manager/Director/Executive" beat "Stormtrooper/Officer/Moff/Sith". Job titles can stay flavorful in document content (a stormtrooper IS a valid Imperial Employee), but role tiers stay corporate.
- They originally specced uv and Python 3.12; they actually run pip + Python 3.11. Always verify their environment before assuming spec values.
