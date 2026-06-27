# HOLOCRON

Classification-aware enterprise RAG over a synthetic Galactic Empire corpus.
See `docs/superpowers/specs/2026-06-27-holocron-design.md` for the design.

## Quickstart (Phase A — Foundation)

Prereqs: Docker Desktop running, Python 3.11 (we use pip + venv), `pnpm` for any local frontend work.

> **Port note:** Postgres is exposed on host **5433** (not 5432) so it doesn't collide
> with any Postgres already installed on the host.

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
cd frontend && pnpm install && pnpm approve-builds --all && cd ..

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
