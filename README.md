# HOLOCRON

Classification-aware enterprise RAG over a synthetic Galactic Empire corpus.
See `docs/superpowers/specs/2026-06-27-holocron-design.md` for the design.

## Quickstart (Phase A — Foundation + Phase B — Retrieval)

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
make backend-install      # creates .venv and installs deps (Phase B adds ~1.5 GB of PyTorch CPU)
make backend-migrate
make backend-seed         # copy the tenant id from the output
make seed-corpus          # one-time, ~60-130s (first run downloads BGE model ~440 MB)
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

The default suite is fast (<25 s) and runs with `-m 'not slow'`. The opt-in
slow test loads the real BGE model and downloads ~440 MB on first run:

```bash
cd backend && .venv/Scripts/python.exe -m pytest -m slow -v
```

### Sample retrieval query (Phase B)

After `make seed-corpus`, with the backend running on port 8000:

```powershell
$tid = "<TENANT_ID_FROM_SEED>"

# Log in as an Executive with HR department (sees both public Handbook and Restricted Supplement)
Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="executive.procurement"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s | Out-Null

$r = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="dress code policy off-base events" } | ConvertTo-Json) `
  -WebSession $s
$r.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Logging in as `employee.security` instead returns only public chunks plus a
refusal block with a reference ID that maps to the withheld chunk IDs in the
`audit_events` table.

> **First-call latency note:** The default embedder is a `lru_cache`d
> singleton, so the BGE model loads once on the *first* `/retrieval/search`
> call (~60 s on a cold process). Subsequent calls are fast. The seed CLI
> already paid this cost, but a fresh `uvicorn` process pays it again on
> its first query. Increase your HTTP client timeout accordingly.

## Layout

- `backend/` — FastAPI + SQLAlchemy + Alembic + LlamaIndex + BGE embeddings
- `frontend/` — Next.js + TypeScript + shadcn/ui
- `corpus/` — 18 synthetic Imperial documents across HR, IT, Security, Engineering, Procurement, Fleet Ops
- `docs/superpowers/` — specs & implementation plans
