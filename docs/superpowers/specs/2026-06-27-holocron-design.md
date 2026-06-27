---
name: HOLOCRON — Classification-Aware Enterprise Knowledge Assistant
status: Approved (design)
date: 2026-06-27
owner: Lutfi
target_window: 4–6 weeks @ ~20 hrs/week (~80–120 hrs MVP)
---

# HOLOCRON — Classification-Aware Enterprise Knowledge Assistant

> *"A holocron's contents are revealed only to those attuned to them."*

A portfolio-grade enterprise RAG system that demonstrates production AI-engineering practice: **clearance-aware retrieval**, **automatic knowledge-conflict detection**, **grounded citations**, **multi-tenant-ready architecture**, and a **lightweight evaluation harness**. The Galactic Empire is the dataset, not the joke — every feature solves a realistic enterprise problem.

---

## 1. Product Vision

HOLOCRON answers questions over an Imperial knowledge base where **what you can retrieve depends on your clearance and department**, and where the assistant **flags contradictions in its own retrieved sources** instead of silently picking one.

The system is designed to look and behave like a production enterprise AI tool. Two flagship capabilities — *classification-aware retrieval* and *conflict detection* — are deliberately uncommon in portfolio projects and combine into one coherent narrative: **enterprise RAG must respect access control AND tell the user when its sources disagree.**

### Headline demos

**Demo A — HR / Employee Handbook (corporate)**
An Imperial Employee and an Imperial Executive both ask: *"What's the dress-code policy for off-base events?"*
- **Imperial Employee** receives the public *Employee Handbook* section, with one citation, plus an honest refusal note: *"2 higher-clearance sources may also be relevant. Request access via Reference #A-7F2C."*
- **Imperial Executive** receives the same answer plus the Restricted *Management Conduct Supplement*, and HOLOCRON flags a side-by-side **conflict card**: the 2023 supplement contradicts the 2019 handbook on permitted off-duty insignia.

**Demo B — Operations (technical)**
An Imperial Employee and an Imperial Director both ask about Death Star reactor coolant shutdown procedures.
- **Imperial Employee** is refused with a reference ID (the topic is Secret/Engineering).
- **Imperial Director** (Engineering) receives the answer with citations to both the 2019 *Reactor Operations Manual* and the 2023 amendment, with a conflict card showing they disagree on shutdown sequence.

Every query, retrieval, refusal, and response is written to an append-only audit log.

> **Roles vs. job titles.** *Clearance tiers* (access level) and *job titles* are separate concepts. A stormtrooper, an engineer, and an accountant can all hold the `employee` tier. A squad leader, a department head, and a Moff can all hold the `manager` or `director` tier. This mirrors how real enterprises separate access tier from job function and makes the RBAC story cleaner.

> **Tenant-agnostic roles, tenant-specific labels.** The `role` column stores the universal corporate ladder (`employee` | `manager` | `director` | `executive`). The "Imperial" prefix is a **display label** owned by the tenant (`tenants.role_label_map`). When Phase 2 introduces the Rebel Alliance tenant, the same `employee` role renders as *"Rebel Operative"* with no schema or RBAC code changes — only a row of labels.

---

## 2. Goals & Non-Goals

### Goals (MVP)

- Classification-aware hybrid retrieval (BM25 + vector) with honest refusal of out-of-clearance content
- Knowledge-conflict detection with side-by-side UI presentation
- Grounded citations linking back to source chunks
- Append-only audit log of every query, retrieval, refusal, and response
- Lightweight evaluation harness (`make eval`) with golden Q&A set and markdown scorecard
- Multi-tenant-ready data model and query layer (single tenant live in MVP)
- Synthetic Imperial corpus with deliberately seeded conflicts and version pairs
- Local-first deployment via Docker Compose; structured JSON logs

### Non-Goals (MVP — deferred or rejected)

- LangChain (overlaps LlamaIndex; defer to Phase 2 only if LangGraph requires it)
- Qdrant (pgvector is sufficient; Qdrant becomes a Phase 2 migration story)
- LangGraph agent workflows (Phase 2)
- Ragas / Langfuse (Phase 2 — MVP uses hand-rolled lightweight eval)
- Approval workflows for documents (Phase 3)
- Time-travel "as-of date" queries (Phase 3)
- Multiple LLM providers behind a switch
- Custom embedding models
- Marketing site / landing page
- Streaming, threaded chat history, "regenerate", "share conversation" UI
- Cloud deployment (Phase 3 — Azure Container Apps)

---

## 3. Two Flagship AI Features (Detailed)

### 3.1 Classification-Aware Hybrid Retrieval

Every chunk is stored with metadata: `(classification, department, version, effective_date, source_doc_id)`.

**Hybrid search:**
- BM25 via Postgres `tsvector` + GIN index (full-text)
- Vector via `pgvector` with `text-embedding-004` (768-dim, cosine)
- Fused via **Reciprocal Rank Fusion** (`k=60`), top-k=6 after fusion

**RBAC filter (applied at SQL level, before fusion):**
```sql
WHERE tenant_id = :tenant
  AND classification_level <= :user_max_clearance
  AND (department = ANY(:user_departments) OR classification_level = 'public')
```

**Honest refusal:** A *parallel* count query runs with the user's clearance ignored. If that count exceeds the filtered count, the response appends:
> *"N higher-clearance sources may also be relevant. Request access via Reference #<short-id>."*

The short-id is logged in the audit table with the exact set of withheld chunk IDs, so an admin can later justify the refusal without exposing content to the user.

### 3.2 Knowledge-Conflict Detection

After retrieval, an additional pass identifies contradictions among top-k chunks.

**Two-stage detection (cost-controlled):**

1. **Heuristic prefilter** — pair chunks where:
   - Same `source_doc_id` family (e.g., "Reactor Manual" lineage) but different `version` or `effective_date`, OR
   - Same `department` and overlapping named entities (extracted at ingest time, stored as a `text[]` column) but different stated numeric values or directives.
   Pairs that survive the prefilter go to stage 2.
2. **LLM-as-judge** — single Gemini call with a structured prompt: *"Do these two passages make incompatible claims about the same subject? Answer JSON: `{conflict: bool, subject: string, position_a: string, position_b: string}`."*

Conflicts are returned alongside the answer and rendered in the UI as a **conflict card** showing both passages, their sources, dates, and clearance badges. The generated answer itself acknowledges the conflict in prose (*"Sources disagree: the 2019 manual specifies X; the 2023 amendment specifies Y."*) rather than picking one silently.

---

## 4. Architecture

### 4.1 System Diagram

```
┌─ Next.js (App Router, TS, shadcn/ui) ─────────────┐
│   /chat   → answer + citations + clearance badges │
│            + conflict cards + refusal notices     │
│   /admin  → upload, doc list, audit log viewer    │
└─────────────────────┬─────────────────────────────┘
                      │ JWT (HttpOnly cookie)
┌─────────────────────▼─────────────────────────────┐
│  FastAPI (backend/app)                            │
│  ├ api/      routers, Pydantic schemas            │
│  ├ services/ ingestion, retrieval, conflict,      │
│  │            answer_generation, audit            │
│  ├ domain/   entities (no framework deps)         │
│  ├ repositories/  data access (SQLAlchemy 2.x)    │
│  ├ workers/  arq jobs (re-embed on doc update)    │
│  └ core/     config, security, tenant context     │
└──────┬────────────────────────┬───────────────────┘
       │                        │
 ┌─────▼─────────┐        ┌─────▼──────┐
 │ Postgres 16   │        │ Gemini     │
 │  + pgvector   │        │ Flash 2.x  │
 │  + tsvector   │        │ (embed +   │
 │  + GIN/HNSW   │        │  generate) │
 └─────┬─────────┘        └────────────┘
       │
 ┌─────▼─────────┐
 │ Redis (arq)   │
 └───────────────┘
```

### 4.2 Backend module boundaries

Each module has one clear purpose, communicates through narrow interfaces, and can be understood without reading another module's internals.

| Module | Purpose | Depends on |
|---|---|---|
| `domain/` | Entities: `Document`, `Chunk`, `User`, `Clearance`, `Department`, `AuditEvent`, `Conflict` | nothing (pure Python) |
| `repositories/` | Data access; one repo per aggregate | `domain/`, SQLAlchemy |
| `services/ingestion/` | Parse → chunk (LlamaIndex) → embed → persist | repos, LlamaIndex |
| `services/retrieval/` | Hybrid search + RBAC filter + RRF | repos |
| `services/conflict_detection/` | Heuristic prefilter + LLM-as-judge | LLM client |
| `services/answer_generation/` | Synthesize grounded answer with citations | LLM client (LlamaIndex `Refine`) |
| `services/audit/` | Append-only event writer | repos |
| `api/` | FastAPI routers, request/response shapes, auth deps | services |
| `workers/` | arq tasks (re-embed on document update) | services |
| `core/` | settings, JWT, tenant-context dependency | none |

**Key boundary rule:** the RBAC filter lives in `repositories/chunk_repository.py` and is unconditional — there is no way to query chunks without passing a `ClearanceContext`. This makes access-control violations impossible at the type level, not just by convention.

### 4.3 Frontend pages

- `/login` — username/password (seeded users for demo)
- `/chat` — single-pane chat with: answer rendering (markdown + inline citation markers `[1]`, `[2]`), citation cards (clearance badge, document title, effective date, snippet), conflict cards (side-by-side), refusal notices
- `/admin/documents` — list, upload form (file + classification + department + effective_date)
- `/admin/audit` — paginated log viewer with filters (user, date range, refusal-only)

Styling via shadcn/ui + Tailwind. No custom component library.

---

## 5. Data Model

```sql
-- tenant column on every table (single tenant active in MVP)

CREATE TABLE tenants (
  id              UUID PRIMARY KEY,
  name            TEXT NOT NULL,                 -- e.g., 'Galactic Empire', 'Rebel Alliance'
  role_label_map  JSONB NOT NULL DEFAULT '{}',   -- per-tenant display labels for the 4 roles,
                                                 -- e.g., {"employee":"Imperial Employee","manager":"Imperial Manager",...}
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TYPE clearance_level AS ENUM ('public', 'restricted', 'secret', 'top_secret');

CREATE TABLE users (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  username        TEXT NOT NULL,
  password_hash   TEXT NOT NULL,
  role            TEXT NOT NULL,          -- tenant-agnostic: 'employee'|'manager'|'director'|'executive'
  max_clearance   clearance_level NOT NULL,
  departments     TEXT[] NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (tenant_id, username)
);

CREATE TABLE documents (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  title           TEXT NOT NULL,
  source_uri      TEXT,                   -- where the file lives (local fs in MVP)
  classification  clearance_level NOT NULL,
  department      TEXT NOT NULL,
  version         TEXT NOT NULL,          -- semver-ish string, free-form
  effective_date  DATE NOT NULL,
  lineage_id      UUID NOT NULL,          -- groups successive versions of "same" doc
  uploaded_by     UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chunks (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal         INT NOT NULL,
  text            TEXT NOT NULL,
  text_tsv        TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding       VECTOR(768),
  -- denormalized from documents for fast filtering
  classification  clearance_level NOT NULL,
  department      TEXT NOT NULL,
  effective_date  DATE NOT NULL,
  lineage_id      UUID NOT NULL,
  entities        TEXT[] DEFAULT '{}',    -- extracted at ingest, for conflict prefilter
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX chunks_embedding_hnsw    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_text_tsv_gin      ON chunks USING gin  (text_tsv);
CREATE INDEX chunks_tenant_cls_dept   ON chunks (tenant_id, classification, department);
CREATE INDEX chunks_lineage           ON chunks (lineage_id);

CREATE TABLE audit_events (
  id              BIGSERIAL PRIMARY KEY,
  tenant_id       UUID NOT NULL,
  user_id         UUID NOT NULL,
  event_type      TEXT NOT NULL,          -- 'query'|'refusal'|'response'|'upload'
  query_text      TEXT,
  retrieved_ids   UUID[],
  withheld_ids    UUID[],
  refusal_ref     TEXT,                   -- short-id used in user-facing refusal
  response_text   TEXT,
  conflicts_found JSONB,
  latency_ms      INT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX audit_user_time ON audit_events (tenant_id, user_id, created_at DESC);
```

---

## 6. Synthetic Corpus

The corpus is **part of the product**, engineered to demonstrate every behavior. ~15-20 markdown documents, ~6-8 hours of writing, living in `corpus/` and ingested via a seed script.

**Required by demo:**

- At least 3 **lineage pairs** (same document, two versions, with conflicting numeric/procedural claims) — e.g., `reactor_manual_2019.md` and `reactor_manual_2023.md` differ on coolant shutdown sequence.
- At least 4 **classification ladders** (same topic at multiple clearance levels) — e.g., public *Employee Recruitment Policy*, Restricted *Manager Hiring Guidelines*, Secret *Executive Search Protocol*.
- At least 2 **cross-department conflicts** — Engineering's safety threshold vs. Fleet Operations' deployment threshold for the same equipment.
- At least 1 **outdated-but-not-superseded** document that should appear in retrieval but be visibly older than alternatives.

Documents follow this frontmatter:

```yaml
---
title: Death Star Reactor Operations Manual
classification: restricted
department: engineering
version: "2.3"
effective_date: 2023-08-01
lineage_id: reactor-manual
---
```

---

## 7. Evaluation Harness

`backend/eval/` contains:

- `golden_set.yaml` — 30-50 Q&A pairs, each tagged with `category` (`lookup` | `refusal` | `conflict` | `cross_department`) and `as_user` (role/clearance to simulate)
- `runner.py` — runs each question, scores along 4 axes:
  - **Retrieval hit-rate**: did expected chunk(s) appear in top-k?
  - **Citation accuracy**: do cited chunks support the answer (LLM-as-judge over `{question, answer, citations}`)?
  - **Refusal correctness**: when expected, did the system refuse? When not expected, did it answer?
  - **Conflict surfacing**: when expected, was the conflict flagged?
- `report.md` template — produces a scorecard per run + diff vs. previous run

Invoked via `make eval`. Output committed to `eval/reports/YYYY-MM-DD.md` for tracking over time.

---

## 8. Project Structure

```
holocron/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   └── admin.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── tenant.py
│   │   ├── domain/
│   │   ├── repositories/
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   ├── retrieval/
│   │   │   ├── conflict_detection/
│   │   │   ├── answer_generation/
│   │   │   └── audit/
│   │   └── workers/
│   ├── eval/
│   │   ├── golden_set.yaml
│   │   ├── runner.py
│   │   └── reports/
│   ├── alembic/                # migrations
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/login/
│   │   ├── chat/
│   │   └── admin/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── corpus/                     # synthetic Imperial documents
│   ├── hr/
│   ├── security/
│   ├── engineering/
│   ├── fleet_ops/
│   └── procurement/
├── docs/
│   ├── superpowers/
│   │   ├── specs/              # design docs (this file)
│   │   └── plans/              # implementation plans (next step)
│   └── architecture/           # diagrams, ADRs
├── scripts/
│   ├── seed_users.py
│   └── seed_corpus.py
├── docker-compose.yml
├── Makefile                    # `make dev`, `make eval`, `make seed`
└── README.md
```

---

## 9. Tech Choices (and what we cut)

| Concern | Choice | Rationale |
|---|---|---|
| Backend lang | Python 3.11 + FastAPI | User strength, async, ecosystem |
| ORM | SQLAlchemy 2.x (async) | mature, pgvector + tsvector friendly |
| Vector store | pgvector + HNSW | one database; Qdrant becomes Phase 2 migration story |
| Full-text | Postgres tsvector + GIN | already there; no extra service |
| Embeddings | Gemini `text-embedding-004` (768-d) | free tier, fast |
| LLM | Gemini Flash 2.x | free tier, fast; DeepSeek swap via env var |
| RAG lib (scoped) | LlamaIndex — loaders, splitters, `BaseNode`, response synthesizer | saves 5-8 hrs on plumbing; orchestration stays in our services |
| Background jobs | arq + Redis | lighter than Celery, async-native |
| Frontend | Next.js 15 + TS + shadcn/ui + Tailwind | fast, looks professional out of the box |
| Auth | JWT in HttpOnly cookie, bcrypt hash | simple, demo-appropriate |
| Container | Docker Compose | local-first; cloud is Phase 3 |
| Eval | Hand-rolled harness | Ragas in Phase 2 |
| Logs | structlog → JSON stdout | drop-in for any platform later |

### Cut from MVP

- **LangChain** — overlaps LlamaIndex; consider only if Phase 2 LangGraph needs it
- **Qdrant** — Phase 2
- **LangGraph** — Phase 2 (agent router)
- **Ragas, Langfuse** — Phase 2
- **Celery** — replaced with arq
- **Multiple LLM providers** — env-var swap only
- **Approval workflows, time-travel queries, second tenant** — Phase 2/3

---

## 10. Phasing

The MVP is delivered in **four implementation phases** (A–D). Each phase ends at a natural demo milestone, has its own implementation plan written by the `writing-plans` skill, and is executed and reviewed before the next plan is written. Post-MVP work is described as Phase 2 and Phase 3 on the roadmap.

### 10.1 MVP Phase A — Foundation (~15–20 hrs)

**Deliverables**
- Project scaffolding: `backend/` (FastAPI, SQLAlchemy 2.x async, pyproject), `frontend/` (Next.js 15 + TS + shadcn), `docker-compose.yml` (Postgres 16 + pgvector + Redis), `Makefile`, README skeleton
- Alembic migrations for `tenants`, `users`, `documents`, `chunks`, `audit_events` tables and `clearance_level` enum
- `core/`: settings, JWT-cookie auth, tenant-context dependency
- `domain/` entities: `User`, `Clearance`, `Department`, `Tenant`
- Auth API: `POST /auth/login`, `GET /auth/me`
- Seeded users: one per clearance tier × at least two departments
- Minimal `/login` page in frontend; on successful login, `/me` shows the user's clearance and departments

**End-of-phase demo:** `docker compose up`, log in as an Imperial Employee and as an Imperial Executive, see your clearance badge.

### 10.2 MVP Phase B — Ingestion + Classification-Aware Retrieval (~25–30 hrs)

**Deliverables**
- Synthetic corpus (~15-20 markdown documents) written in `corpus/` with frontmatter — includes lineage pairs, classification ladders, cross-department conflicts (per §6)
- `services/ingestion/`: LlamaIndex `SimpleDirectoryReader` + frontmatter parser → `SemanticSplitterNodeParser` (sentence fallback) → `GeminiEmbedding` → persist via `ChunkRepository`
- `scripts/seed_corpus.py` (idempotent re-ingest)
- `repositories/chunk_repository.py` with unconditional `ClearanceContext`-aware query API
- `services/retrieval/`: hybrid search (BM25 via tsvector + vector via pgvector) fused with RRF (k=60), top-k=6
- Honest-refusal counting (parallel unfiltered count → reference ID generation)
- `POST /retrieval/search` endpoint returning ranked chunks + refusal metadata
- Integration tests covering: clearance filter correctness, department filter, refusal-counting accuracy, RRF ranking

**End-of-phase demo:** `curl POST /retrieval/search` as different users returns clearance-appropriate results with refusal references where applicable.

### 10.3 MVP Phase C — Conflict Detection + Frontend (~25–30 hrs)

**Deliverables**
- Entity extraction at ingest time (lightweight NER, populate `chunks.entities`)
- `services/conflict_detection/`: heuristic prefilter (lineage-pair OR same-department-overlapping-entities) → LLM-as-judge (Gemini, structured JSON output) → in-memory LRU cache
- `services/answer_generation/`: LlamaIndex `Refine` / `CompactAndRefine` synthesizer producing answers with inline `[1]`, `[2]` citation markers; conflict-acknowledging prose when conflicts exist
- `POST /chat/ask` endpoint orchestrating retrieval → conflict detection → answer generation
- Frontend `/chat`: chat UI (shadcn), citation cards (clearance badge + document title + effective date + snippet), conflict cards (side-by-side), refusal notices
- Frontend `/admin/documents`: upload form (file + classification + department + effective_date), document list

**End-of-phase demo:** Both headline demos (§1) reproduce end-to-end in the browser.

### 10.4 MVP Phase D — Eval, Audit, and Polish (~15–20 hrs)

**Deliverables**
- `services/audit/`: append-only writer wired to chat and retrieval endpoints
- Frontend `/admin/audit`: paginated viewer with filters (user, date range, refusal-only)
- `backend/eval/`: `golden_set.yaml` (30–50 Q&A pairs across the four categories), `runner.py` scoring against the four axes (§7), markdown scorecard template
- `make eval` invocation; first scorecard committed to `eval/reports/`
- structlog → JSON stdout configuration across backend
- Fresh-machine `docker compose up` validated end-to-end (< 10 min)
- README: 60-second demo script, architecture diagram (rendered), eval methodology, 3-minute walkthrough video link, runbook for adding new corpus documents
- Definition-of-Done checklist (§13) verified

**End-of-phase demo:** `make eval` produces a green scorecard; audit viewer shows the demo session; recordable end-to-end demo video.

### 10.5 Post-MVP Phase 2 (~40–60 hrs, after MVP ships)

- LangGraph agent router (classify query as `lookup` | `comparison` | `summarize_many` and dispatch)
- Qdrant adapter + migration write-up + benchmark comparison vs. pgvector
- Ragas integration in eval harness (faithfulness, answer relevance, context precision)
- Langfuse traces wired to existing structlog spans
- Second tenant ('Rebel Alliance') live to prove multi-tenancy
- Streaming responses where it's cheap

### 10.6 Post-MVP Phase 3 (~40-60 hrs)

- Approval workflows: documents move `draft → in_review → approved → archived`; only `approved` is retrievable
- Time-travel queries: "what did the Procurement Policy say on stardate X?" with version-pinned retrieval
- Azure Container Apps deployment; OpenTelemetry traces
- Per-tenant configuration (clearance taxonomy, departments)

---

## 11. Portfolio & Interview Value (mapping)

| Feature | Recruiter value | Interview value |
|---|---|---|
| Classification-aware retrieval | "Production-grade access control in an AI system" | RBAC at the data layer vs. post-filter, side-channel leakage concerns, refusal-without-leak design |
| Conflict detection | Memorable demo moment | Cost control (heuristic + LLM), LLM-as-judge prompt design, false-positive trade-offs |
| Hybrid search (BM25 + vector + RRF) | "Knows retrieval isn't just embeddings" | Why RRF over weighted-sum, choosing `k=60`, sparse-dense complementarity |
| Lightweight eval harness | "Has shipped without guessing" | Designing a golden set, evaluating refusals, regression vs. drift |
| Append-only audit log | "Understands compliance" | Append-only design, withheld-content references, immutability |
| Multi-tenant-ready data model | "Has built SaaS" | Tenant isolation at SQL layer, dependency-injection for tenant context |
| Clean architecture (domain/services/repos) | "Senior engineer" | Where the RBAC filter lives and why, dependency direction |
| Synthetic corpus engineered for demos | "Thinks about the whole product" | Why deterministic conflicts matter for eval |

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Conflict detection adds latency and LLM cost | Heuristic prefilter, top-k=6 cap, in-memory LRU cache keyed on `(question_hash, retrieved_ids)` |
| Gemini free-tier rate limits during eval runs | Small golden set, cached embeddings, `LLM_PROVIDER` env var to swap to DeepSeek |
| Synthetic corpus is hidden work | Explicitly budgeted (6-8 hrs); seeded conflicts double as eval-set fixtures |
| 6-week budget overruns | Cut order: frontend polish → admin audit viewer UI (use API instead) → conflict UI niceties. **Eval is never cut.** |
| LlamaIndex version churn | Pin to a single minor version; avoid bleeding-edge features; restrict use to documented stable primitives |
| Demo-time LLM outages | Cache golden-set responses for offline demo |

---

## 13. Definition of Done (MVP)

- All MVP goals in §2 are implemented and reachable from the UI
- 30+ golden Q&A pairs pass; eval scorecard checked into `eval/reports/`
- `docker compose up` brings up a working system on a fresh machine in < 10 minutes
- README includes: 60-second demo script, architecture diagram, 3-minute walkthrough video link, eval methodology
- Audit log shows every demo query (verifiable in `/admin/audit`)
- Refusal flow is reproducible: an Imperial Employee account exists, asking a Top-Secret question produces the refusal message with a reference ID
- Conflict flow is reproducible: one canonical question produces the side-by-side conflict card
- All four MVP phases (A–D) have shipped against their end-of-phase demos
