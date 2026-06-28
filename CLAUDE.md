# HOLOCRON — Claude session handoff

> **For Claude:** This file is loaded automatically. Read it first, then read the spec, the latest plan, and the latest completion record before doing anything.

## What this project is

**HOLOCRON** is a portfolio-grade enterprise RAG system over a synthetic Galactic Empire corpus. Two flagship capabilities are the demo: **classification-aware retrieval** (clearance-filtered hybrid search + honest refusal) and **knowledge-conflict detection** (LLM-as-judge flags contradictions side-by-side). Built by a senior full-stack dev (`.NET`/Python/PostgreSQL background) transitioning into AI Engineering.

## Source-of-truth documents (read in this order)

1. **Design spec:** [docs/superpowers/specs/2026-06-27-holocron-design.md](docs/superpowers/specs/2026-06-27-holocron-design.md) — full product, architecture, data model, MVP phasing
2. **Phase A plan + completion:** [plan](docs/superpowers/plans/2026-06-27-phase-a-foundation.md) · [completion](docs/superpowers/plans/2026-06-27-phase-a-foundation-completion.md)
3. **Phase B spec + plan + completion:** [spec](docs/superpowers/specs/2026-06-27-phase-b-ingestion-retrieval.md) · [plan](docs/superpowers/plans/2026-06-27-phase-b-ingestion-retrieval.md) · [completion](docs/superpowers/plans/2026-06-27-phase-b-ingestion-retrieval-completion.md)
4. **Phase C spec + plan + completion:** [spec](docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md) · [plan](docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat.md) · [completion](docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md)
5. **Original brief:** [initial_idea.txt](initial_idea.txt) — untracked; the user's starting prompt

## Phase status

- **Phase A — Foundation:** ✅ done (auth, RBAC scaffolding, schema, seeded users, /login + /me UI)
- **Phase B — Ingestion + Classification-Aware Retrieval:** ✅ done (corpus, ingestion pipeline, hybrid RBAC-filtered retrieval, honest-refusal with audit, `POST /retrieval/search`)
- **Phase C — Conflict Detection + Frontend:** ✅ done — code complete, 131 tests passing (~30s). **Manual browser walkthrough of spec §7.1 is intentionally deferred** by the user until after Phase D; the two demos will be verified together at the end. See the [Phase C completion record](docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md) for state, deviations, and Phase D follow-ups.
- **Phase D — Eval + Audit + Polish:** ⏭ next. No spec or plan yet — start with `superpowers:brainstorming` against design spec §10.4 + the Phase C completion record's Phase D follow-up list.

## Tech stack as actually built (not what the spec listed)

| Concern | Choice | Notes |
|---|---|---|
| Python | **3.11** (not 3.12) | User runs 3.11 locally. Don't use PEP 695 / `@override` / 3.12-only syntax. |
| Python deps | **pip + venv** (not `uv`) | `uv` was not installed; plan was switched. `pyproject.toml` uses setuptools + `[project.optional-dependencies].dev`. |
| Backend | FastAPI 0.115, async SQLAlchemy 2.x, asyncpg, Alembic | pydantic v2 + pydantic-settings |
| Auth | JWT in HttpOnly cookie (PyJWT), bcrypt hashes | Cookie name: `holocron_session` |
| Postgres | pgvector/pgvector:pg16 via Docker | **Host port 5433** (not 5432) — avoids conflict with user's existing host Postgres install |
| Redis | redis:7-alpine via Docker | Not wired yet; for arq jobs (deferred — not in MVP) |
| Embeddings | **Local `BAAI/bge-base-en-v1.5`** (768-dim) via sentence-transformers | NOT Gemini. PyTorch CPU is installed (~1.5 GB). First model load downloads ~440 MB, cached at `~/.cache/huggingface`. |
| LLM | **Groq `llama-3.3-70b-versatile`** primary → `llama-3.1-8b-instant` fallback | NOT Gemini. Replaces spec's Gemini Flash. Free API; needs `GROQ_API_KEY` env var. |
| NLP | **spaCy `en_core_web_sm`** (NER + lemma-lowered noun_chunks) for ingest-time entity extraction | One-time `python -m spacy download en_core_web_sm` (~50 MB). Full default pipeline (parser + lemmatizer required). |
| RAG library | LlamaIndex `SentenceSplitter` (not `SemanticSplitter`) | Spec called for SemanticSplitter; deferred — quality lift was marginal and ingest cost doubled. Revisit in Phase D if eval signals demand it. |
| Frontend | Next.js 15.0.0, React 19 RC, TypeScript, Tailwind v3, shadcn/ui | App Router, no `src/` dir |
| Frontend pkg mgr | pnpm 11 — **one-time `pnpm approve-builds --all`** required after fresh install (sharp + unrs-resolver) |
| Container base | `python:3.11-slim` backend, `node:22-alpine` frontend | |

## Critical conventions

### Phase A (still hold)

- **Roles are tenant-agnostic, labels are per-tenant.** `users.role` stores `'employee' | 'manager' | 'director' | 'executive'`. Display labels live in `tenants.role_label_map`. Never hard-code "Imperial X" in code or queries — read from the tenant.
- **Multi-tenant from day one.** Every table has `tenant_id`. Every repository read takes a `tenant_id` parameter — no exceptions.
- **Classification levels are TEXT + CHECK, not Postgres ENUM.** asyncpg required casts; CHECK gives identical validation without friction.
- **Per-test DB fixture recreates schema each test.** Bulletproof against pytest-asyncio loop-scope issues on Windows + asyncpg.
- **`User.__init__` overrides `departments` default to `[]`** (also true for `Chunk.entities`). SQLAlchemy 2.x `Mapped`'s `default=list` only applies on DB insert, not on Python construction.
- **`Settings.cors_origins` uses `Annotated[..., NoDecode]`.** Without this, pydantic-settings JSON-parses comma-separated env vars before validators run and fails.

### Phase B additions

- **RBAC is type-enforced at the repository layer.** Every read on `ChunkRepository` requires a `ClearanceContext` parameter. There is no `get_all_chunks()` — only `bm25_topn(ctx, ...)` / `vector_topn(ctx, ...)`. The one explicit bypass is `unfiltered_topn_ids(...)`, named so its use is grep-able. Used solely for refusal counting.
- **`Chunk` Python attribute is `text_`, not `text`.** SQL column is `text` via `mapped_column("text", ...)` override. The trailing underscore avoids shadowing the imported `sqlalchemy.text` function in the class body. Constructor kwarg is `text_=...`. If you read chunk content in Python, use `chunk.text_`.
- **`EmbeddingProvider` is a Protocol.** Production uses `BgeEmbeddingProvider` via the `get_default_embedder()` `@lru_cache` factory. Tests inject `FakeEmbeddingProvider` (deterministic hash-based 768-d vectors). The API router uses `Depends(get_default_embedder)` so the test fixture can override it.
- **conftest pre-creates `vector` and `pgcrypto` extensions** before `Base.metadata.create_all`. The `db_session` fixture runs `CREATE EXTENSION IF NOT EXISTS vector;` and `pgcrypto;` because the test fixture uses `create_all` directly (no Alembic). Without this, every chunk test fails.
- **Default pytest deselects `@pytest.mark.slow` tests.** `addopts = "-ra -m 'not slow'"`. The two real-BGE tests in `tests/test_embedding_bge.py` are opt-in: `pytest -m slow`.
- **`AuditRepository` is intentionally minimal in Phase B.** Only `insert_query` and `insert_refusal`. Full `services/audit/` with event taxonomy + viewer is Phase D. Light Phase B writes exist so refusal reference IDs are actually traceable from day one.
- **Retrieval module layout deviates from the spec.** Spec had `services/retrieval/{bm25,vector}.py` submodules. Final layout collapses both into `ChunkRepository` methods (repositories own SQL). `services/retrieval/` keeps `rrf.py` (pure fusion), `refusal.py` (ref-id + audit), and `__init__.py::search` (orchestration).
- **First `/retrieval/search` call after a fresh uvicorn process takes ~60s.** Lazy BGE load via the `lru_cache` singleton. Subsequent calls are fast. Bump HTTP client timeouts when smoke-testing.
- **`text_tsv` uses `Computed(persisted=True)` in the ORM but reads use raw SQL.** `bm25_topn` and friends use `sqlalchemy.text(...)` for the `plainto_tsquery` + `ts_rank` calls — cleaner inline than expression builder.

### Phase C additions

- **`chunks.entities` is now populated by spaCy at ingest.** The entity extractor (`services/ingestion/entity_extractor.py`) uses the full default spaCy pipeline — the plan's original `disable=["parser","lemmatizer"]` was removed during execution because `parser` is required for `doc.noun_chunks` (raises E029) and `lemmatizer` is required for `token.lemma_` to return non-empty strings.
- **`LLMClient` Protocol covers BOTH the conflict-judge path (`complete_json`) and the answer-generation path (`complete_text`).** Production = `GroqLLMClient` with 6-attempt retry ladder (3 primary + 3 fallback). Final-attempt sleep is skipped to avoid wasted tail latency. Tests inject `FakeLLMClient` with scripted responses.
- **Conflict cache is module-global in `services/conflict_detection/judge.py`** keyed on sorted `(chunk_id_a, chunk_id_b)` tuples, capacity 256, FIFO-evicted (labelled LRU in the spec — functional difference is zero at this cap). Cleared by `_judge_cache_clear()` in tests; transient `LLMUnavailable` failures are NOT cached.
- **`RetrievalResult` now carries `lineage_id: uuid.UUID` and `entities: tuple[str, ...]`** so the conflict prefilter has everything it needs without a second DB round-trip. Phase B's `ChunkHit` and `ChunkRepository` SELECTs were updated accordingly.
- **`services/answer_generation/` implements the LlamaIndex `CompactAndRefine` *pattern*** (compact context block + single LLM call) without using the LlamaIndex synthesizer object directly. This keeps the retry/fallback policy in one place and tests deterministic. The refine template (`REFINE_TEMPLATE_STR`) is provided for future use; not currently exercised because top-k=6 (~3K tokens) fits in one compaction.
- **`generate_answer` re-assigns `Position.marker`** from the chunk-position index in the final list (judge emits `marker=0` as a sentinel). API marker numbering and `[n]` chip targets in the frontend all share the same enumeration of the unfiltered retrieval results — the citations list filters to only-cited but preserves the original marker.
- **`POST /chat/ask` returns `LLMUnavailable` as HTTP 503**; latency is measured across the full retrieval+detection+generation chain and written to `audit_events.latency_ms`.

## Local dev quickstart

```powershell
# 1. Start services (assumes Docker Desktop running)
docker compose up -d postgres redis

# 2. Backend (one-time)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"           # ~1.5 GB; pulls PyTorch CPU
python -m spacy download en_core_web_sm     # one-time, ~50 MB
python -m alembic upgrade head
python scripts/seed_users.py                # prints tenant id + seeded usernames
python scripts/seed_corpus.py               # ~130s first run (BGE download ~440 MB)

# 3. Frontend (one-time)
cd ..\frontend
pnpm install
pnpm approve-builds --all                   # one-time; otherwise pnpm dev fails preflight
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

Currently: **131 tests, all passing** (default `-m 'not slow'`, ~28–32 s). Plus 4 opt-in slow tests (`pytest -m slow`): 2 real-BGE from Phase B + 2 real-spaCy from Phase C.

**Known flake:** `tests/test_security.py::test_tampered_token_rejected` flakes occasionally — Phase A test that random-mutates JWT bytes and has non-zero false-pass probability. Always passes on rerun. Hardening deferred to Phase D.

## Corpus

`corpus/` holds **18 synthetic Imperial documents** (~39 chunks after BGE ingest with default `chunk_size=512`). Distribution:

- HR ×7 (employee handbook + management supplement = Demo A pair, compensation handbook, remote work [outdated], recruitment + manager hiring guidelines [ladder], onboarding audit)
- IT ×3 (acceptable use, access provisioning, incident response [secret])
- Security ×3 (access audit, insider threat [secret], executive search [secret])
- Engineering ×2 (reactor manual 2019 + 2023 = Demo B pair with shutdown-sequence conflict)
- Procurement ×2 (2020 + 2024 lineage pair with credit-threshold conflict)
- Fleet Ops ×1 (executive search protocol [top_secret])

Spec §6 coverage: 3 lineage pairs · 4 classification ladders (dress code, recruitment, IT access, executive search) · 2 cross-dept conflicts (HR/Security audit cadence, IT/Security incident response timing) · 1 outdated-but-not-superseded doc.

## Demo accounts (all password: `imperial-march`)

| Username                | Tier      | Departments               | Sees in Demo A (dress code) |
|-------------------------|-----------|---------------------------|---|
| employee.security       | Employee  | security                  | Public Handbook only + refusal |
| employee.engineering    | Employee  | engineering               | Public Handbook only + refusal |
| manager.hr              | Manager   | hr                        | Public + Restricted supplement |
| manager.engineering     | Manager   | engineering               | Public Handbook only + refusal |
| director.engineering    | Director  | engineering               | Public Handbook only + refusal |
| director.security       | Director  | security                  | Public Handbook only + refusal |
| executive.fleet         | Executive | fleet_operations,security | Public Handbook only + refusal (no HR dept!) |
| executive.procurement   | Executive | procurement,hr            | Public + Restricted supplement |

> **Demo A path:** use `executive.procurement` (has hr) vs `employee.security` for the contrast. `executive.fleet` doesn't see the HR supplement because clearance + department both gate access.

## Resuming next session — Phase D entry point

**No code starts until Phase D has a spec + plan.** Recommended sequence:

1. **`superpowers:brainstorming`** against design spec §10.4 (which sketches Phase D scope) plus the prioritized Phase D backlog below. Surface decisions: scope cuts, eval-harness shape, audit-viewer UX, observability format, whether to ship streaming.
2. **`superpowers:writing-plans`** to turn the brainstormed decisions into a TDD task list at `docs/superpowers/plans/<date>-phase-d-<topic>.md`.
3. **`superpowers:subagent-driven-development`** or `superpowers:executing-plans` against that plan.
4. **End-of-Phase-D demo** walks BOTH the Phase C §7.1 checklist AND any Phase D demo paths in one browser session.

### Phase D backlog (prioritized; from Phase C completion record + final review)

**Tier 1 — do before broad eval**
- **Warm BGE + spaCy + Groq at startup.** The 60s first-`/chat/ask` stall is a demo-killer for anyone except the author. Cheap fix; do first.
- **Drop `llama-index-llms-groq` dep OR actually use it.** Currently dead weight — spec decision #5 (`CompactAndRefine` *synthesizer*) drifted to "pattern only". Either revert to a real LlamaIndex synthesizer or remove the dep + update the spec.
- **Add a `correlation_id`** linking the three audit row writes (`query`, `response`, optional `refusal`) per `/chat/ask`. Required before any audit-viewer work is coherent. Cheaper to add at write time than backfill.

**Tier 2 — quality + correctness**
- **Filter conflicts whose chunks aren't in the final list.** Defensive guard against silent `marker=0` if dataflow ever drifts.
- **Make `_judge_cache_clear` an autouse pytest fixture.** Currently called manually in every judge-touching test — easy to forget; module-global cache will silently leak across cases.
- **Convert bounded cache from FIFO to true LRU** (touch-on-hit) — to actually match spec #3.
- **`AuditRepository` is intentionally minimal.** Full `services/audit/` with event taxonomy + viewer (`/admin/audit`) is Phase D.
- **structlog → JSON stdout.** Design spec §2.

**Tier 3 — eval & polish**
- **Evaluation harness** + `golden_set.yaml` + `make eval`. Drives all "is this actually better" decisions.
- **`chunk_size=512` may be too large** for our ~600–1500 word docs (39 chunks across 18 docs). Eval will tell.
- **Disk cache for Groq responses** — only if eval shows repeated same-prompt calls. Eval-gated, not unconditional.
- **`/admin/documents` upload + list page.**
- **Streaming responses** for `/chat/ask`.
- **Replace `SentenceSplitter` with `SemanticSplitter`** if eval signals demand it.

**Tier 4 — tech debt cleanup (5–15 min each)**
- **Migrate `ChunkRepository` SELECT row reads to `.mappings()`.** Positional `row[7]`/`row[9]` reads will silently break on next schema column add.
- **Simplify `GroqLLMClient._sleep` shim** — drop `inspect.isawaitable`, either standardize on `async lambda` in tests or DI the sleep function.
- **Fix pre-existing `frontend/app/layout.tsx` Geist font import error** — Phase A scaffold imports `Geist`/`Geist_Mono` from `next/font/google`, which the installed `next` version doesn't expose. Either upgrade `next` or swap to `Inter`. Doesn't block dev server but pollutes `tsc --noEmit`.
- **Update `pyproject.toml` deps + spec/plan docs** to reflect actual constraint: `llama-index-llms-groq>=0.3,<0.4` (0.2.x conflicts with Phase B's locked `llama-index-core`).
- **Add a real-Groq slow test** (`@pytest.mark.slow`) for `/chat/ask` end-to-end. Phase C only has real-spaCy + real-BGE slow tests.
- **Harden `tests/test_security.py::test_tampered_token_rejected`** — Phase A JWT-fuzz test with non-zero false-pass probability.
- **arq + Redis re-embed worker.** Deferred from MVP; revisit if eval workload demands batching.
- **Backend without `--reload` doesn't auto-reload code changes.** Document if it bites others.

### Non-functional notes that bit during Phase C

- **`llama-index-llms-groq` version range deviated from spec** (`>=0.2,<0.3` → `>=0.3,<0.4`) because 0.2.x requires `llama-index-core<0.12` which conflicts with Phase B's locked core.
- **Phase A's `ClearanceBadge` component had prop `level: ClearanceLevel`**; renamed to `classification: Clearance` to match Phase C's chat type. The Phase A consumer at `frontend/app/me/page.tsx` was updated in the same Task 15 commit (one-line rename).
- **Frontend Docker build still fails on Docker Desktop networking quirk.** Phase A/B/C all work fine with `pnpm dev`. Retry `docker compose build frontend` when the network is healthy. Not blocking.

## How to collaborate with this user

- They picked the 4-phase MVP split deliberately — each phase ends at a demoable milestone. Don't merge phases or skip the end-of-phase demo.
- They lean **recommendation-first**: present 2–3 options with a clear recommended pick rather than asking open-ended.
- They want **enterprise-corporate framing**, not military/Star Wars-heavy framing. "Imperial Employee/Manager/Director/Executive" beat "Stormtrooper/Officer/Moff/Sith". Job titles can stay flavorful in document content (a stormtrooper IS a valid Imperial Employee), but role tiers stay corporate. Phase B corpus reads like real internal policies — keep that voice.
- They originally specced uv + Python 3.12 + Gemini; they actually run pip + Python 3.11 + Groq + local BGE. **Always verify their environment before assuming spec values.**
- During Phase B they asked for "more numbers and specific data" in corpus docs — they want retrieval to surface concrete figures, not vague prose. Carry this into any Phase C answer-generation prompt design.
- During Phase B they expanded HR + added IT mid-execution. They're comfortable revising the plan when it serves the demo — but they like to know the impact (coverage requirements, schema changes) before saying yes.
