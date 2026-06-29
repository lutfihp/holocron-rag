---
name: HOLOCRON Phase D — Eval, Audit, and Polish
status: Locked (brainstorm)
date: 2026-06-28
owner: Lutfi
phase: D
target_window: ~15–20 hrs
predecessors:
  - docs/superpowers/specs/2026-06-27-holocron-design.md
  - docs/superpowers/specs/2026-06-27-phase-b-ingestion-retrieval.md
  - docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md
  - docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md
---

# HOLOCRON Phase D — Eval, Audit, and Polish

## 1. Goal

Phase D closes the MVP. End state is a **portfolio-demoable system**, not production-ready. The phase ends at one demo milestone that walks the Phase B and Phase C demo paths together with the new Phase D capabilities (eval scorecard, audit viewer, structured logs).

Phase D does NOT add new product capabilities. It ships the harness and observability layers that prove the existing capabilities work and stay working, plus the targeted tech-debt items that would otherwise rot.

## 2. In-scope deliverables

Nine items, ordered by dependency:

1. **Task 0 — Hygiene** (~45 min)
   - Fix Phase A `frontend/app/layout.tsx` Geist font import (blocks `tsc --noEmit` clean).
   - Add `_judge_cache_clear` as an autouse pytest fixture (prevents test contamination as eval tests grow).
   - Correct `pyproject.toml` Groq dep version range to `llama-index-llms-groq>=0.3,<0.4` (matches what's installed; Phase B's `llama-index-core>=0.12,<0.13` lock requires it).
   - Update Phase C spec/plan docs to reflect actual deviations from the completion record (entity-extractor pipeline, dep version, `_sleep` shim).

2. **Audit schema — `correlation_id`** (~1 hr)
   - Add `correlation_id UUID NOT NULL` column to `audit_events`; Alembic migration with index on `(tenant_id, correlation_id)`.
   - Thread `correlation_id` through `/chat/ask` so the 2–3 events for one request share it.
   - **Bundled tech-debt:** migrate `ChunkRepository` SELECTs to `.mappings()` (named-column access). Repository SQL is being touched anyway; low marginal cost; eliminates positional `row[7]`/`row[9]` breakage risk on the next column add.

3. **LlamaIndex `CompactAndRefine` synthesizer** (~2 hrs)
   - Implement a thin `HolocronGroqLLM` adapter (LlamaIndex `LLM` interface) that forwards to existing `GroqLLMClient.complete_text`. Retry/fallback stays in `GroqLLMClient` — adapter is wire-only.
   - Replace pattern-only implementation in `services/answer_generation/` with `CompactAndRefine.synthesize()`.
   - Amend Phase C spec decision #5 to reflect that the synthesizer ships for real.

4. **Startup warming** (~1.5 hrs)
   - FastAPI lifespan event: sync-load BGE embedder + warm one embed call; sync-load spaCy `en_core_web_sm`; async-spawn Groq client probe.
   - Env var `HOLOCRON_SKIP_WARMUP` (unset by default; dev `--reload` workflow sets to `1`).
   - `GET /healthz/ready` returns 200 only when warm; 503 otherwise.

5. **structlog + correlation_id binding** (~2 hrs)
   - Configure structlog with JSON renderer for prod, console renderer for dev (controlled by `HOLOCRON_LOG_PRETTY`).
   - FastAPI middleware binds `correlation_id` to `structlog.contextvars` at request start; clears at end.
   - Migrate backend imports from `logging.getLogger` → `structlog.get_logger`.
   - uvicorn access logs stay default (out of scope).

6. **Evaluation harness** (~6–7 hrs — largest single item)
   - `backend/eval/golden_set.yaml` — 30 questions: 12 lookup, 8 refusal, 6 conflict, 4 cross_department. Expectations are `lineage_id`-based, not chunk-ID-based.
   - `backend/eval/runner.py` — runs two passes:
     - **Retrieval-only:** calls `POST /retrieval/search` directly. Scores retrieval hit-rate and refusal correctness.
     - **Full-stack:** calls `POST /chat/ask`. Scores all four axes including LLM-as-judge citation accuracy (single Groq call per question, JSON output).
   - `make eval` target.
   - First scorecard committed to `eval/reports/2026-MM-DD.md` (markdown) + `.json` sidecar for future diffing.

7. **`/admin/audit` viewer** (~3 hrs)
   - Backend: `GET /admin/audit?cursor=...&user_id=...&start=...&end=...&has_refusal=...&has_conflict=...`. Cursor pagination by `(created_at DESC, id)`. Rows aggregated server-side by `correlation_id`.
   - Frontend: single-page table at `/admin/audit`. One row per correlation_id. Filter bar on top. Click row → inline expand showing query/retrieved/withheld/response/conflicts/latency. Role-gated to `director` and `executive` via existing RBAC dep.

8. **README + 60s demo script + architecture diagram** (~2 hrs)
   - Update root `README.md`: quickstart, 60-second demo script (executive.procurement dress-code → employee.security refusal → director.engineering reactor + conflict), eval methodology summary, rendered architecture diagram (mermaid source + checked-in SVG).

9. **Manual browser walkthrough** (~30 min + 1 hr bug-fix buffer)
   - Walk Phase C §7.1 checklist (8 items) + Phase D additions (audit viewer reachable, `/healthz/ready` returns 200, eval scorecard exists in `eval/reports/`).
   - Update Phase C completion record with browser-verification ticks.
   - Allocate 1 hr buffer in this task for any bugs uncovered.

## 3. Out of scope

Deferred to Post-MVP Phase 2 or future cleanup pass:

- `/admin/documents` upload + list UI (seed_corpus.py covers demo)
- Real-Groq slow test (`@pytest.mark.slow`)
- Streaming `/chat/ask` (SSE) — conflict-card-before-stream needs Phase 2 design
- arq + Redis re-embed worker
- General disk cache for Groq responses (eval-driven; revisit if eval shows hot repeats). Note: a narrow eval-only judge cache is in scope (see §13).
- LlamaIndex SemanticSplitter swap (eval-driven)
- Conflict cache FIFO → true LRU (functional difference = 0 at cap=256)
- `_sleep` shim cleanup in `GroqLLMClient` (cosmetic)
- `tests/test_security.py::test_tampered_token_rejected` flake hardening
- CI eval-smoke (eval stays local-only)

## 4. Locked architectural decisions

1. **Eval expectations are `lineage_id`-based, not chunk-ID-based.** Chunk UUIDs regenerate on every `seed_corpus.py` run; lineage IDs are author-controlled in frontmatter and stable.
2. **Eval runs two passes.** Retrieval-only via `POST /retrieval/search` (fast, deterministic axes); full-stack via `POST /chat/ask` (all four axes including LLM-judged citation accuracy). The split localizes regressions to retrieval vs generation.
3. **Eval is local-only.** No CI integration. Scorecards committed manually to `eval/reports/`. Reason: portfolio project has no PR-racing team to gate, and CI Groq quota cost is not worth it.
4. **`/admin/audit` rows group by `correlation_id`** server-side. One physical `/chat/ask` = one visual row, expanding inline to show its 2–3 underlying `audit_events`.
5. **Audit pagination is cursor-based** on `(created_at DESC, id)`. Avoids offset-pagination drift as new events arrive during browsing.
6. **`correlation_id` is required** (`NOT NULL`) on `audit_events` and threaded through `/chat/ask` end-to-end. No backfill — existing demo audit rows can be truncated before applying the migration if needed; Phase D demo will repopulate.
7. **`.mappings()` migration bundled with audit schema change.** Repository SELECTs touch the same column space; one PR, one risk window.
8. **Startup warming is hybrid:** BGE + spaCy load sync inside the FastAPI lifespan event; Groq client probe is async (fire-and-forget). `HOLOCRON_SKIP_WARMUP=1` skips for `--reload` dev workflow.
9. **`/healthz/ready` returns 200 only when warm.** Frontend MAY gate `/chat` on it (nice-to-have, not required for Phase D demo). Portfolio value: K8s-shaped readiness probe artifact.
10. **LlamaIndex `CompactAndRefine` synthesizer ships for real** via a thin `HolocronGroqLLM` adapter wrapping `GroqLLMClient.complete_text`. Retry/fallback stays in `GroqLLMClient` (adapter is wire-only). Phase C spec decision #5 is amended in Task 0 to match.
11. **structlog rolls out across backend Python** (every service that logs). uvicorn access logs stay default. `correlation_id` binds via a `structlog.contextvars` middleware.
12. **Logging output mode is env-controlled.** `HOLOCRON_LOG_PRETTY=1` → console renderer (dev). Unset → JSON renderer (prod, eval, demo recording).
13. **Streaming responses deferred to Phase 2.** Pre-baked interview answer: conflict cards need full retrieval + judge results before render, so streaming requires either a separate conflict channel or a pre-stream conflict payload — both are Phase 2 design.
14. **Task 0 hygiene is front-loaded.** Geist font, autouse fixture, pyproject version correction, doc updates land in one ~45-min task before larger changes touch the same files.
15. **Phase D ends with one combined Phase B+C+D demo walkthrough.** Phase C's deferred §7.1 checklist is verified inside the Phase D end-of-phase demo, not separately.

## 5. Data model deltas

```sql
-- Alembic migration: add correlation_id to audit_events
ALTER TABLE audit_events
  ADD COLUMN correlation_id UUID NOT NULL;

CREATE INDEX audit_correlation
  ON audit_events (tenant_id, correlation_id);
```

No other schema changes. Existing `audit_events` rows from manual Phase C testing can be truncated before applying the migration if backfill is undesirable.

## 6. API surface

New endpoints:

- `GET /healthz/ready` — returns `{"ready": bool, "checks": {"bge": bool, "spacy": bool}}`. 200 when all checks true, 503 otherwise.
- `GET /admin/audit` — query params: `cursor?`, `user_id?`, `start?`, `end?`, `has_refusal?`, `has_conflict?`, `limit?` (default 50, max 200). Returns correlation-grouped audit rows. Role-gated to `director` and `executive`.

`POST /chat/ask` external contract unchanged; internally, audit writes now carry `correlation_id`.

## 7. Eval harness shape

### golden_set.yaml entry format

```yaml
- id: <stable-slug>
  category: lookup | refusal | conflict | cross_department
  as_user: <username from seeded set>
  question: <natural language>
  expected:
    must_refuse: bool
    must_cite_lineages: [<lineage_id>, ...]    # retrieval hit-rate
    refusal_min_withheld: int?                 # refusal category only
    must_flag_conflict: bool                   # conflict + cross_department
    conflict_subject_keywords: [str, ...]      # conflict + cross_department
```

### Scoring axes

| Axis | Method | Applies to |
|---|---|---|
| Retrieval hit-rate | `must_cite_lineages` ⊆ retrieved lineages in top-k | lookup, conflict, cross_department |
| Refusal correctness | `must_refuse` matches `response.refusal` presence + (if set) `refusal_min_withheld` ≤ withheld count | refusal |
| Conflict surfacing | any returned conflict's `subject` substring-matches a `conflict_subject_keywords` entry | conflict, cross_department |
| Citation accuracy | LLM-as-judge: for each `[n]` marker, does the cited chunk's text support the surrounding sentence? Single Groq call per question, JSON output, score ∈ [0, 1]. | lookup, conflict, cross_department |

### Output

- `eval/reports/YYYY-MM-DD.md` — markdown scorecard with per-category breakdown, aggregate pass rate, and diff vs last committed run (regressions + improvements lists).
- `eval/reports/YYYY-MM-DD.json` — machine-readable sidecar for future tooling.

### Runtime

~2 min full local `make eval` on 30 questions (full-stack pass dominates). Retrieval-only pass alone ~30s.

## 8. /admin/audit viewer

### Backend response shape

```json
{
  "rows": [
    {
      "correlation_id": "uuid",
      "user_id": "uuid",
      "username": "executive.procurement",
      "first_event_at": "2026-06-28T...",
      "latency_ms": 1834,
      "had_refusal": false,
      "had_conflict": true,
      "event_count": 2,
      "events": [
        { "event_type": "query", "query_text": "...", "retrieved_ids": ["..."], "...": "..." },
        { "event_type": "response", "response_text": "...", "conflicts_found": [], "...": "..." }
      ]
    }
  ],
  "next_cursor": "opaque-string-or-null"
}
```

Server-side aggregation by `correlation_id` ordered by max `created_at` desc. Cursor encodes `(last_row_first_event_at, last_correlation_id)` so pagination is stable under concurrent writes.

### Frontend (`/admin/audit`)

- Sticky filter bar on top: user select, date range, has-refusal toggle, has-conflict toggle.
- Table: one row per correlation_id. Columns: time, user, latency, refusal badge, conflict badge.
- Row click → inline expand (no navigation). Shows raw event payloads in collapsible sections.
- "Load more" button at bottom uses cursor; no infinite scroll.
- Role gate: 403 for non-director/executive (existing FastAPI dep on the router).

## 9. Startup warming

FastAPI lifespan event sketch:

```python
async def lifespan(app: FastAPI):
    if not os.getenv("HOLOCRON_SKIP_WARMUP"):
        await _warm_sync()  # BGE load + 1 embed; spaCy load + 1 parse
        asyncio.create_task(_warm_groq_async())  # fire-and-forget TLS probe
    app.state.ready = True
    yield
```

`/healthz/ready` reads `app.state.ready` and per-component flags set during `_warm_sync`.

Dev workflow: `HOLOCRON_SKIP_WARMUP=1 uvicorn ... --reload` — first request after reload pays the ~50s cost; subsequent ones don't.

## 10. Logging

`backend/app/core/logging.py` (sketch):

```python
def configure_logging():
    pretty = bool(os.getenv("HOLOCRON_LOG_PRETTY"))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if pretty else structlog.processors.JSONRenderer(),
        ],
    )
```

FastAPI middleware (sketch):

```python
@app.middleware("http")
async def correlation_id_middleware(request, call_next):
    cid = request.headers.get("x-correlation-id") or str(uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    try:
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response
    finally:
        structlog.contextvars.clear_contextvars()
```

Inside `/chat/ask`, the same `cid` is used as `audit_events.correlation_id`. The log record and the audit row carry the same identifier.

## 11. Migration / sequencing

Task order (mirrors §2):

1. **Task 0 hygiene** — no dependencies; safe first.
2. **Audit schema + `.mappings()`** — prereq for Task 7 viewer.
3. **LlamaIndex synthesizer wire-up** — independent of audit work.
4. **Startup warming** — independent.
5. **structlog + correlation_id binding** — uses `correlation_id` UUID generator from Task 2.
6. **Eval harness** — runs against everything above; effective catch-all integration test.
7. **`/admin/audit` viewer** — uses Task 2 schema + Task 5 correlation_id.
8. **README + 60s demo + architecture diagram** — last; reflects shipped state.
9. **Manual browser walkthrough** — gate before declaring Phase D done.

Critical path: 2 → 5 → 7. Eval (6) can run in parallel with viewer (7) once 2 + 5 are done.

## 12. Exit criteria + end-of-phase demo

Phase D is done when ALL of:

- [ ] 9 in-scope deliverables shipped per §2.
- [ ] `make eval` runs end-to-end and produces a scorecard committed to `eval/reports/`.
- [ ] `/admin/audit` viewer reachable as `executive.procurement`; shows demo session rows grouped by correlation_id.
- [ ] First `/chat/ask` after `/healthz/ready` returns 200 completes in under 5s (warming verified).
- [ ] Backend logs are JSON when `HOLOCRON_LOG_PRETTY` is unset, pretty when set; `correlation_id` appears on every log line inside a request.
- [ ] README quickstart works end-to-end on a fresh machine in under 10 min.
- [ ] Manual browser walkthrough covers Phase C §7.1 checklist (all 8 items) + Phase D additions (audit viewer, `/healthz/ready`, scorecard file).
- [ ] `pytest` default suite still passes (target: ~150 tests including new eval-related unit tests).
- [ ] `tsc --noEmit` runs clean (Geist font fix verified).

## 13. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Eval LLM-as-judge (citation accuracy) eats Groq quota during prompt iteration | Cache judge calls by `(question, answer, citations)` hash during `make eval`. Cache stored in `eval/.cache/` (gitignored). Narrow scope — eval-only, NOT the general Groq-response disk cache that was cut. |
| Eval runtime drifts past 2 min as golden_set grows | Hard cap at 30 entries for Phase D; growth deferred to Phase 2. |
| `/admin/audit` server-side grouping query is slow at scale | At demo scale (<1000 rows) any reasonable GROUP BY works. Production-scale optimization is Phase 3. |
| Startup warming makes `--reload` painful | `HOLOCRON_SKIP_WARMUP=1` env var; document in README dev section. |
| structlog rollout breaks existing tests via log capture | Run full suite after migration. Phase C completion record reports no assertions on log content, so failure mode is bounded. |
| LlamaIndex `CompactAndRefine` synthesizer output differs enough from pattern-only output to regress eval scores | Run eval before AND after the synthesizer swap; commit both scorecards. Roll back to pattern-only if regression > 5% on aggregate pass rate. |
| Phase D end-of-phase demo finds bugs Phase C deferred | 1 hr buffer allocated in Task 9 for bug-fixes uncovered during walkthrough. |
| Cursor encoding for `/admin/audit` pagination is leaky | Encode as base64-JSON of `{first_event_at, correlation_id}`; opaque to client; validated server-side. |
