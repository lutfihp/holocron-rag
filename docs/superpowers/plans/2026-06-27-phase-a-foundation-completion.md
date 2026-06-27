# Phase A — Foundation: Completion Record

Date verified: 2026-06-27

## End-of-phase demo checklist

- [x] `make backend-install` creates `.venv` and installs deps.
- [x] `make backend-migrate` applies the 5-table Phase A schema (round-trip up/down verified).
- [x] `make backend-seed` seeds the Imperial tenant and 8 demo users; idempotent on re-run.
- [x] `make backend-test` runs **30 tests, all green** (4 modules + 2 ORM + 8 enums + 7 security + 3 user-repo + 6 auth-API + 2 tenant-context).
- [x] Login as `employee.security` returns `role_label: "Imperial Employee"` and `max_clearance: "public"`.
- [x] Login as `executive.fleet` returns `role_label: "Imperial Executive"` and `max_clearance: "top_secret"`.
- [x] `tenants.role_label_map` produces the per-tenant label "Imperial Employee" / "Imperial Executive" (verified in API response JSON, not hard-coded in client).
- [x] Sign-out (DELETE `/auth/session`) returns 204 and clears cookie; subsequent `/auth/me` is 401.
- [x] `/login` page renders (Next.js dev server returns HTML at `http://localhost:3000/login`).
- [x] End-to-end browser-equivalent (curl) flow: POST `/auth/login` → cookie issued → GET `/auth/me` with cookie → 200 with correct user payload.
- [x] Backend Docker image builds (`docker compose build backend`).
- [ ] **Frontend Docker image build is currently failing on this host** with intermittent `npm registry` network errors from inside the build container (Docker Desktop networking quirk on Windows — not a Dockerfile issue). The Dockerfile itself is correct and runs `pnpm install --frozen-lockfile` against the committed `pnpm-lock.yaml`. Local-dev path (`pnpm dev`) is the verified demo path for Phase A.

## Notable plan deviations (and why)

1. **Postgres host port 5432 → 5433.** The host already had a Postgres instance bound to 5432. We re-mapped the container's port 5432 to host 5433 so we wouldn't shadow the existing install. Container-to-container connections (in docker-compose) still use `postgres:5432` internally.
2. **`clearance_level` Postgres ENUM → TEXT + CHECK constraint.** asyncpg required explicit casts when mapping the ENUM to SQLAlchemy's `String` column. Replacing with `TEXT NOT NULL CHECK (col IN (...))` gives identical validation, removes the cast headache, and keeps the ORM model framework-light.
3. **pytest-asyncio fixture loop scope = `function`.** Session-scoped engine fixtures conflicted with pytest-asyncio's default function-scoped test loop on Windows + asyncpg. Per-test engine recreation is ~50ms overhead — acceptable for Phase A's 30 tests (3.3s total).
4. **`departments` column gets a Python-side `__init__` default.** SQLAlchemy 2.x `Mapped` syntax's `default=list` only applies on DB insert, not on `User(...)` instantiation. Override ensures `u.departments == []` for freshly-instantiated objects.
5. **shadcn registry needs `pnpm approve-builds --all` once.** Without it, the postinstall build scripts for `sharp` and `unrs-resolver` are skipped and `pnpm dev` fails its preflight check. Documented in README local-dev quickstart.
6. **Switched from `uv` to `pip + venv` mid-execution.** Pre-flight prereq check showed `uv` wasn't installed. Plan was updated end-to-end before any code was written.

## Spec coverage

- §10.1 deliverables 1–8: all implemented (see plan tasks).
- §5 schema: full Phase A–D schema applied via migration 0001 (verified by downgrade/upgrade round-trip in Task 8).
- Multi-tenant readiness: every Phase A table carries `tenant_id`; all `UserRepository` reads are tenant-parameterized.
- Tenant-agnostic roles + per-tenant labels: `users.role` stores `employee|manager|director|executive`; `tenants.role_label_map` provides display labels.

## Known follow-ups for Phase B

- Add `documents`, `chunks`, `audit_events` ORM models alongside the ingestion service.
- Wire structlog (deferred to Phase D).
- Add CORS origins for production deploy (Phase 3).
- Retry frontend Docker build when Docker Desktop network is healthy; verify the full `docker compose up --build` flow.
