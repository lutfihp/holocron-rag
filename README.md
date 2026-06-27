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
