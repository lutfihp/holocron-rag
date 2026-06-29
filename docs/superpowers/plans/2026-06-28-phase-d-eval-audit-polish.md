# Phase D — Eval, Audit, and Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase D end-to-end: front-loaded tech-debt hygiene, `audit_events.correlation_id` schema + threading + `.mappings()` migration, real LlamaIndex `CompactAndRefine` synthesizer via a thin Groq adapter, FastAPI startup warming with `/healthz/ready`, structlog JSON logging with `correlation_id` binding, a 30-question eval harness with `make eval` and a committed scorecard, an `/admin/audit` viewer (backend + frontend) with cursor-based correlation-grouped pagination, README polish with rendered architecture diagram, and a final manual browser walkthrough that closes the deferred Phase C §7.1 demo checklist.

**Architecture:** Phase D adds no new product capability. It adds (a) one schema column (`correlation_id`) that ties together the 2–3 audit rows per `/chat/ask`, (b) one structlog middleware that binds the same id to every log record inside the request, (c) one FastAPI lifespan event that warms BGE + spaCy synchronously and probes Groq asynchronously, (d) one LlamaIndex adapter that lets us swap the pattern-only answer generator for a real `CompactAndRefine` synthesizer without duplicating retry logic, (e) one `backend/eval/` package with `runner.py` + `golden_set.yaml` + Makefile target that scores retrieval and full-stack responses across four axes, and (f) one `/admin/audit` page that groups events by `correlation_id` and renders them in a click-to-expand table.

**Tech Stack:** Python 3.11 · FastAPI · async SQLAlchemy 2.x · Alembic · pgvector · structlog · LlamaIndex `CompactAndRefine` · `llama-index-llms-groq` · Groq API · PyYAML · Next.js 15 · React 19 · TypeScript · Tailwind + shadcn/ui · Mermaid CLI (for architecture SVG).

**Source spec:** [docs/superpowers/specs/2026-06-28-phase-d-eval-audit-polish.md](../specs/2026-06-28-phase-d-eval-audit-polish.md)

---

## File map

**Backend — new:**

- `backend/alembic/versions/0002_phase_d_audit_correlation.py` — migration: add `correlation_id` + index
- `backend/app/core/logging.py` — `configure_logging()`, console vs JSON renderer toggle
- `backend/app/core/warmup.py` — `_warm_sync()`, `_warm_groq_async()`, warm-state flags
- `backend/app/api/healthz.py` — `GET /healthz/ready` router
- `backend/app/api/admin.py` — `GET /admin/audit` router
- `backend/app/repositories/audit_repository.py` — extend to query rows for the viewer (new method `list_grouped_by_correlation`)
- `backend/app/services/answer_generation/groq_llm_adapter.py` — `HolocronGroqLLM` (LlamaIndex `LLM` interface) forwarding to `GroqLLMClient`
- `backend/eval/__init__.py`
- `backend/eval/golden_set.yaml` — 30 question entries
- `backend/eval/runner.py` — orchestrator: load YAML → run two passes → write scorecard
- `backend/eval/scorer.py` — pure scoring functions (retrieval, refusal, conflict, citation-judge)
- `backend/eval/report.py` — markdown + JSON serializers, diff vs last run
- `backend/eval/prompts.py` — `CITATION_JUDGE_PROMPT`
- `backend/eval/.gitignore` — ignore `.cache/`
- `backend/eval/reports/.gitkeep`
- `Makefile` — add `eval` target (create at repo root if missing)

**Backend — modified:**

- `backend/app/domain/models.py` — add `correlation_id` to `AuditEvent`
- `backend/app/repositories/audit_repository.py` — all three `insert_*` methods take `correlation_id`
- `backend/app/repositories/chunk_repository.py` — migrate SELECT row reads to `.mappings()` for `bm25_topn`, `vector_topn`, `unfiltered_topn_ids`
- `backend/app/api/chat.py` — generate `correlation_id` at top of `post_ask`, pass to audit writes
- `backend/app/api/retrieval.py` — bind `correlation_id` for retrieval-only audit (if any); harmless if absent
- `backend/app/services/answer_generation/__init__.py` — `generate_answer` accepts an `LLM` adapter and uses `CompactAndRefine`; keep `FakeLLMClient` fast-path
- `backend/app/services/answer_generation/llm_client.py` — `get_default_synthesizer()` returns a `CompactAndRefine` synthesizer wrapping `HolocronGroqLLM(default_llm)`
- `backend/app/main.py` — `lifespan` context, structlog config call, correlation_id middleware, register `healthz_router` + `admin_router`
- `backend/app/core/config.py` — `log_pretty: bool`, `skip_warmup: bool`
- `backend/tests/conftest.py` — autouse `_judge_cache_clear` fixture
- `backend/pyproject.toml` — add `structlog`, `pyyaml`

**Backend — tests (new):**

- `backend/tests/test_audit_correlation.py` — schema + threading
- `backend/tests/test_chunk_repository_mappings.py` — repository SELECTs return named-column rows
- `backend/tests/test_groq_llm_adapter.py` — thin-adapter forwards correctly
- `backend/tests/test_answer_generation_synthesizer.py` — `generate_answer` uses `CompactAndRefine` end-to-end with a fake
- `backend/tests/test_warmup.py` — `_warm_sync()` flips flags; `_warm_groq_async()` is fire-and-forget
- `backend/tests/test_healthz.py` — `/healthz/ready` 503 → 200 transitions
- `backend/tests/test_logging.py` — JSON vs console renderer; correlation_id binding round-trips
- `backend/tests/test_correlation_middleware.py` — request gets/echoes `x-correlation-id` header
- `backend/tests/test_admin_audit_endpoint.py` — pagination, filters, role gate
- `backend/tests/test_eval_scorer.py` — each scoring axis as a pure function
- `backend/tests/test_eval_runner.py` — runner orchestrates a single question against a mocked API
- `backend/tests/test_eval_report.py` — markdown + JSON output shape; diff vs prior run

**Frontend — new:**

- `frontend/app/admin/layout.tsx` — role gate (director/executive)
- `frontend/app/admin/audit/page.tsx` — viewer page
- `frontend/app/admin/audit/components/AuditFilters.tsx` — sticky filter bar
- `frontend/app/admin/audit/components/AuditRow.tsx` — collapsed row + expanded inline detail
- `frontend/app/admin/audit/components/AuditEventDetail.tsx` — renders a single event payload
- `frontend/lib/audit-api.ts` — typed fetch wrapper
- `frontend/lib/types/audit.ts` — `AuditRow`, `AuditEvent`, `AuditQuery`

**Frontend — modified:**

- `frontend/app/layout.tsx` — fix Geist font import (Task 0)
- `frontend/app/chat/page.tsx` — optional: gate on `/healthz/ready` (not required; deferred to demo time)

**Docs — modified/new:**

- `README.md` (root) — quickstart, 60-second demo script, eval methodology, embedded architecture SVG link
- `docs/architecture/holocron-system.mmd` (new) — mermaid source
- `docs/architecture/holocron-system.svg` (new) — rendered diagram
- `docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md` — amend decision #5 (synthesizer ships for real)
- `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat.md` — note deviations from Phase C completion record
- `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md` — tick browser-verification items
- `docs/superpowers/plans/2026-06-28-phase-d-eval-audit-polish-completion.md` (new at end of Phase D)
- `CLAUDE.md` — update Phase status to Phase D ✅; mark Phase D backlog items as done; describe `/healthz/ready` + `make eval` in quickstart

---

## Conventions for this plan

- All backend commands run from `backend/` with `.venv` activated.
- All frontend commands run from `frontend/` with pnpm.
- "Commit" steps use `git commit -m "..."` with single-line messages. Pre-commit hooks (if any) must pass; on failure, fix and create a NEW commit.
- Tests use `pytest -v <path>` for narrow runs and `pytest` for the default (non-slow) suite.
- The default suite must stay green after each task. Currently 131 passing; target end-of-phase-D is ~155+ tests.
- TDD discipline: write failing test → run → verify FAIL → implement minimal → run → verify PASS → commit. Migrations and YAML data files are exceptions (no pure-TDD path); they have an explicit "write file → run/inspect → write test" order called out per step.

---

## Task 0: Hygiene (front-loaded tech-debt)

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `backend/tests/conftest.py`
- Modify: `docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md`
- Modify: `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat.md`

### Step 0.1: Fix Geist font import

- [ ] **Open `frontend/app/layout.tsx` and replace the `next/font/google` `Geist`/`Geist_Mono` imports with `Inter`.**

Replace the import block at top of file with:

```tsx
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
```

In the `<body>` element, replace `className={`${geistSans.variable} ${geistMono.variable} antialiased`}` with:

```tsx
className={`${inter.variable} antialiased font-sans`}
```

- [ ] **Verify `tsc --noEmit` clean:**

```bash
cd frontend && pnpm tsc --noEmit
```

Expected: zero errors. If the project lacks a `tsc` script, run `pnpm exec tsc --noEmit` instead.

- [ ] **Commit:**

```bash
git add frontend/app/layout.tsx
git commit -m "fix(frontend): replace Geist font with Inter to unblock tsc --noEmit"
```

### Step 0.2: Add `_judge_cache_clear` autouse fixture

- [ ] **Write the fixture in `backend/tests/conftest.py`.** Add at the bottom of the file:

```python
import pytest


@pytest.fixture(autouse=True)
def _clear_judge_cache():
    """Phase D: module-global conflict-judge cache must not leak across tests.

    Runs before every test (autouse). Calling _judge_cache_clear is cheap and
    idempotent. Without this autouse, tests that exercise judge.py reuse cache
    entries seeded by earlier tests, producing flake on re-ordering.
    """
    from app.services.conflict_detection.judge import _judge_cache_clear
    _judge_cache_clear()
    yield
```

- [ ] **Run the existing judge tests to confirm they still pass:**

```bash
cd backend && pytest tests/test_conflict_judge.py tests/test_conflict_detection.py -v
```

Expected: all pass. Also remove any **manual** `_judge_cache_clear()` calls inside test bodies (now redundant). Search for them with Grep on `_judge_cache_clear`.

- [ ] **Run full default suite:**

```bash
pytest
```

Expected: 131 passed (Phase C baseline). If any flake, investigate before continuing.

- [ ] **Commit:**

```bash
git add backend/tests/conftest.py backend/tests/test_conflict_judge.py backend/tests/test_conflict_detection.py
git commit -m "test(conflict): autouse _judge_cache_clear fixture; drop manual calls"
```

### Step 0.3: Update Phase C docs to match completion record

The Phase C completion record (`docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`) lists 7 deviations from the original plan. Two of them — the spaCy pipeline `disable` removal and the `_sleep` shim — are still material; one (the `llama-index-llms-groq` version range) is already reflected in `pyproject.toml`. Update the spec and plan documents so they don't lie about the shipped code.

- [ ] **Amend Phase C spec decision #5 in `docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md`.**

Find the section describing decision #5 ("Answer generation uses LlamaIndex `CompactAndRefine`..."). Add a paragraph at the end:

```markdown
> **Phase D amendment (2026-06-28):** Phase C shipped a pattern-only implementation
> (compact context block + single LLM call) without invoking the LlamaIndex
> synthesizer object. Phase D Task 2 replaces this with a real `CompactAndRefine`
> synthesizer via a thin `HolocronGroqLLM` adapter wrapping `GroqLLMClient`.
> Retry/fallback policy remains in `GroqLLMClient`; the adapter is wire-only.
```

- [ ] **Amend Phase C plan to note deviations.** In `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat.md`, find Task 1 (spaCy entity extractor) and add the note:

```markdown
> **Shipped deviation (see completion record):** the `_load_spacy()` function does NOT
> pass `disable=["parser","lemmatizer"]` as drafted. The parser is required for
> `doc.noun_chunks`; the lemmatizer is required for `token.lemma_`. The full
> default pipeline is loaded.
```

Then find the `GroqLLMClient._sleep` step and add:

```markdown
> **Shipped deviation:** `_run_with_ladder` uses `inspect.isawaitable(self._sleep(...))`
> to support both sync and async `_sleep` overrides in tests. Phase D Tier 4 backlog
> notes this as cosmetic cleanup; deliberately deferred.
```

- [ ] **Commit:**

```bash
git add docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat.md
git commit -m "docs(phase-c): amend spec + plan to match shipped deviations"
```

---

## Task 1: Audit `correlation_id` schema + threading + `.mappings()` migration

**Files:**
- Create: `backend/alembic/versions/0002_phase_d_audit_correlation.py`
- Modify: `backend/app/domain/models.py`
- Modify: `backend/app/repositories/audit_repository.py`
- Modify: `backend/app/repositories/chunk_repository.py`
- Modify: `backend/app/api/chat.py`
- Create: `backend/tests/test_audit_correlation.py`
- Create: `backend/tests/test_chunk_repository_mappings.py`

### Step 1.1: Write the Alembic migration

- [ ] **Create `backend/alembic/versions/0002_phase_d_audit_correlation.py`:**

```python
"""phase D: add correlation_id to audit_events

Revision ID: 0002_phase_d_audit_correlation
Revises: 0001_phase_a_initial
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_phase_d_audit_correlation"
down_revision = "0001_phase_a_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No backfill: Phase C demo audit rows (if any) are wiped before this migration.
    # If any rows exist they will fail NOT NULL; that is intentional — the project
    # has no production data and re-seeding via the demo path is trivial.
    op.execute("TRUNCATE TABLE audit_events")
    op.add_column(
        "audit_events",
        sa.Column("correlation_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "audit_correlation",
        "audit_events",
        ["tenant_id", "correlation_id"],
    )


def downgrade() -> None:
    op.drop_index("audit_correlation", table_name="audit_events")
    op.drop_column("audit_events", "correlation_id")
```

- [ ] **Apply the migration against the dev DB:**

```bash
cd backend && alembic upgrade head
```

Expected: prints `Running upgrade 0001_phase_a_initial -> 0002_phase_d_audit_correlation`.

- [ ] **Verify schema via psql:**

```bash
docker compose exec postgres psql -U holocron -d holocron -c "\d audit_events"
```

Expected: `correlation_id | uuid | not null` in the column list, and `audit_correlation` index on `(tenant_id, correlation_id)`.

### Step 1.2: Update the `AuditEvent` ORM model

- [ ] **In `backend/app/domain/models.py`, locate the `AuditEvent` class** and add the column. The exact line depends on the file but it sits next to `tenant_id`. Add:

```python
correlation_id: Mapped[uuid.UUID] = mapped_column(
    PG_UUID(as_uuid=True), nullable=False, index=False
)
```

(Index is already created by the migration; don't double-register.)

### Step 1.3: TDD — `AuditRepository` requires `correlation_id` on all inserts

- [ ] **Write the failing test in `backend/tests/test_audit_correlation.py`:**

```python
import uuid
import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_query_persists_correlation_id(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    cid = uuid.uuid4()
    repo = AuditRepository(db_session)

    await repo.insert_query(
        tenant_id=tenant_id,
        user_id=user_id,
        correlation_id=cid,
        query_text="who runs hr?",
        retrieved_ids=[],
    )
    await db_session.flush()

    row = (await db_session.execute(select(AuditEvent))).scalar_one()
    assert row.correlation_id == cid
    assert row.event_type == "query"


@pytest.mark.asyncio
async def test_three_events_share_one_correlation_id(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    cid = uuid.uuid4()
    repo = AuditRepository(db_session)

    await repo.insert_query(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        query_text="q", retrieved_ids=[],
    )
    await repo.insert_refusal(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        reference_id="ref", retrieved_ids=[], withheld_ids=[],
    )
    await repo.insert_response(
        tenant_id=tenant_id, user_id=user_id, correlation_id=cid,
        response_text="r", conflicts_found=None, latency_ms=42,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 3
    assert {r.correlation_id for r in rows} == {cid}
```

Note: `seeded_tenant_user` is a new fixture you need to add to `conftest.py` if it doesn't exist. It should return `(tenant_id, user_id)` from a freshly-seeded tenant + user. If existing tests already provide this through a different fixture name, reuse that name and skip adding the new fixture.

- [ ] **Run the test — verify it FAILS:**

```bash
pytest tests/test_audit_correlation.py -v
```

Expected: `TypeError: insert_query() got an unexpected keyword argument 'correlation_id'` (the current methods don't take it).

### Step 1.4: Add `correlation_id` parameter to all three `AuditRepository` methods

- [ ] **In `backend/app/repositories/audit_repository.py`, update all three methods:**

```python
async def insert_query(
    self,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    correlation_id: uuid.UUID,
    query_text: str,
    retrieved_ids: Sequence[uuid.UUID],
) -> None:
    self._session.add(
        AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
            event_type="query",
            query_text=query_text,
            retrieved_ids=list(retrieved_ids),
        )
    )

async def insert_refusal(
    self,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    correlation_id: uuid.UUID,
    reference_id: str,
    retrieved_ids: Sequence[uuid.UUID],
    withheld_ids: Sequence[uuid.UUID],
) -> None:
    self._session.add(
        AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
            event_type="refusal",
            refusal_ref=reference_id,
            retrieved_ids=list(retrieved_ids),
            withheld_ids=list(withheld_ids),
        )
    )

async def insert_response(
    self,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    correlation_id: uuid.UUID,
    response_text: str,
    conflicts_found: dict | None,
    latency_ms: int,
) -> None:
    self._session.add(
        AuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
            event_type="response",
            response_text=response_text,
            conflicts_found=conflicts_found,
            latency_ms=latency_ms,
        )
    )
```

- [ ] **Run the test — verify it PASSES:**

```bash
pytest tests/test_audit_correlation.py -v
```

Expected: 2 passed.

- [ ] **Update all callers.** The audit-call sites are in `backend/app/api/chat.py` (one `insert_response`) and `backend/app/services/retrieval/__init__.py` or `refusal.py` (where `insert_query` and `insert_refusal` get called). Grep them:

```bash
grep -rn "insert_query\|insert_refusal\|insert_response" backend/app
```

For each call site, add `correlation_id=cid` where `cid` is plumbed from the caller. Step 1.5 handles the `/chat/ask` end of this plumbing; the retrieval-service callers receive `correlation_id` via the orchestrator argument (see Step 1.5).

### Step 1.5: Thread `correlation_id` through `/chat/ask`

- [ ] **In `backend/app/api/chat.py`, at the top of `post_ask`** (right after the empty-query guard), generate the id:

```python
import uuid

# ... in post_ask, after the empty-query 400 guard:
correlation_id = uuid.uuid4()
```

- [ ] **Pass `correlation_id` into the retrieval `search(...)` call** if the orchestrator writes audit rows. Update its signature in `backend/app/services/retrieval/__init__.py` to accept and forward `correlation_id` to its internal `AuditRepository` calls.

- [ ] **Pass `correlation_id` into the `insert_response` call** at the bottom of `post_ask`:

```python
await audit.insert_response(
    tenant_id=ctx.tenant_id,
    user_id=ctx.user_id,
    correlation_id=correlation_id,
    response_text=answer.text,
    conflicts_found={"count": len(answer.conflicts), "subjects": [c.subject for c in answer.conflicts]},
    latency_ms=latency_ms,
)
```

- [ ] **Write the integration test** in `backend/tests/test_chat_endpoint.py` (extend existing). Test that a single `/chat/ask` produces N audit rows (2 or 3) all sharing one `correlation_id`:

```python
@pytest.mark.asyncio
async def test_chat_ask_audit_rows_share_correlation_id(client, seeded_chunk, fake_llm_payload):
    resp = await client.post("/chat/ask", json={"query": "test"}, cookies=auth_cookies("executive.fleet"))
    assert resp.status_code == 200

    # Re-open a session and read audit_events for this request:
    async with TestSessionLocal() as s:
        rows = (await s.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().all()
    assert len(rows) >= 2  # query + response (+ refusal if applicable)
    assert len({r.correlation_id for r in rows}) == 1
```

- [ ] **Run the test:**

```bash
pytest tests/test_chat_endpoint.py::test_chat_ask_audit_rows_share_correlation_id -v
```

Expected: PASS.

### Step 1.6: Migrate `ChunkRepository` SELECTs to `.mappings()`

The current pattern in `bm25_topn`, `vector_topn`, `unfiltered_topn_ids` uses positional row access (`row[0]`, `row[7]`, etc.). Migrate to `.mappings()` so reads access columns by name.

- [ ] **Write the failing test in `backend/tests/test_chunk_repository_mappings.py`:**

```python
"""Phase D: smoke-test that .mappings() reads work — main signal is that
existing repository tests still pass after the refactor. This file just
asserts the return-shape contract."""
import pytest

from app.repositories.chunk_repository import ChunkHit


def test_chunk_hit_has_all_columns_needed_downstream():
    """ChunkHit signature is what the orchestrator depends on. Sanity check
    that no field was lost during the .mappings() migration."""
    fields = {f for f in ChunkHit.__dataclass_fields__}
    assert {
        "chunk_id", "document_id", "document_title", "classification",
        "department", "effective_date", "snippet", "score", "rank",
        "lineage_id", "entities",
    } <= fields
```

This test passes today. The actual safety net is **the existing test suite** — `tests/test_chunk_repository.py`, `tests/test_retrieval_service.py`, `tests/test_retrieval_api.py`. If we break the .mappings() migration, those break.

- [ ] **In `backend/app/repositories/chunk_repository.py`, migrate `bm25_topn`:**

Replace the result-iteration block with:

```python
result = await self._session.execute(sql, {
    "tenant": ctx.tenant_id,
    "allowed": allowed_levels(ctx.max_clearance),
    "depts": list(ctx.departments),
    "q": query,
    "n": n,
})
return [
    ChunkHit(
        chunk_id=row["id"],
        document_id=row["document_id"],
        document_title=row["title"],
        classification=row["classification"],
        department=row["department"],
        effective_date=row["effective_date"],
        snippet=row["text"],
        score=float(row["score"]),
        rank=idx + 1,
        lineage_id=row["lineage_id"],
        entities=list(row["entities"] or []),
    )
    for idx, row in enumerate(result.mappings().all())
]
```

Repeat the same pattern for `vector_topn` and `unfiltered_topn_ids`. The SQL stays the same; only the result-iteration changes. For `vector_topn`, the score conversion `1.0 - row["distance"]` stays in the comprehension.

- [ ] **Run all repository + retrieval tests:**

```bash
pytest tests/test_chunk_repository.py tests/test_retrieval_service.py tests/test_retrieval_api.py tests/test_chunk_repository_mappings.py -v
```

Expected: all pass.

- [ ] **Run full suite:**

```bash
pytest
```

Expected: still green (target ~133 passing — added 3 new tests in Task 1).

### Step 1.7: Commit Task 1

```bash
git add backend/alembic/versions/0002_phase_d_audit_correlation.py \
        backend/app/domain/models.py \
        backend/app/repositories/audit_repository.py \
        backend/app/repositories/chunk_repository.py \
        backend/app/api/chat.py \
        backend/app/services/retrieval \
        backend/tests/test_audit_correlation.py \
        backend/tests/test_chunk_repository_mappings.py \
        backend/tests/test_chat_endpoint.py \
        backend/tests/conftest.py
git commit -m "feat(audit): add correlation_id to audit_events; migrate ChunkRepository to .mappings()"
```

---

## Task 2: LlamaIndex `CompactAndRefine` synthesizer via thin adapter

**Files:**
- Create: `backend/app/services/answer_generation/groq_llm_adapter.py`
- Modify: `backend/app/services/answer_generation/__init__.py`
- Modify: `backend/app/services/answer_generation/llm_client.py`
- Create: `backend/tests/test_groq_llm_adapter.py`
- Create: `backend/tests/test_answer_generation_synthesizer.py`

### Step 2.1: TDD — `HolocronGroqLLM` adapter forwards to `GroqLLMClient`

- [ ] **Write the failing test in `backend/tests/test_groq_llm_adapter.py`:**

```python
import pytest

from app.services.answer_generation.groq_llm_adapter import HolocronGroqLLM
from app.services.answer_generation.llm_client import FakeLLMClient


@pytest.mark.asyncio
async def test_adapter_acomplete_forwards_to_inner_client():
    inner = FakeLLMClient(text_responses=["adapter response"])
    adapter = HolocronGroqLLM(inner_client=inner)

    response = await adapter.acomplete("hello")

    assert response.text == "adapter response"
    assert inner.calls_text == ["hello"]


@pytest.mark.asyncio
async def test_adapter_complete_sync_path_uses_event_loop_runner():
    inner = FakeLLMClient(text_responses=["sync response"])
    adapter = HolocronGroqLLM(inner_client=inner)

    # CompactAndRefine internals MAY call .complete (sync) in some paths; the adapter
    # must defer to asyncio.run / get_event_loop() and forward to inner.complete_text.
    response = adapter.complete("sync prompt")

    assert response.text == "sync response"


def test_adapter_metadata_class_name():
    """LlamaIndex registers LLMs by class_name. Lock the public name."""
    inner = FakeLLMClient()
    adapter = HolocronGroqLLM(inner_client=inner)
    assert adapter.metadata.model_name == "holocron-groq"
```

- [ ] **Run — verify FAIL:**

```bash
pytest tests/test_groq_llm_adapter.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.answer_generation.groq_llm_adapter'`.

### Step 2.2: Implement `HolocronGroqLLM`

- [ ] **Create `backend/app/services/answer_generation/groq_llm_adapter.py`:**

```python
"""Thin adapter exposing GroqLLMClient through the LlamaIndex `LLM` interface
so `CompactAndRefine.synthesize()` can drive answer generation.

Retry / fallback / rate-limit handling lives in `GroqLLMClient`; this adapter
forwards calls and converts response shapes. Do not add behavior here.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
    LLMMetadata,
    MessageRole,
)
from llama_index.core.llms.custom import CustomLLM

from app.services.answer_generation.llm_client import LLMClient


@dataclass
class HolocronGroqLLM(CustomLLM):
    """LlamaIndex `LLM` interface forwarding to an internal `LLMClient`."""

    inner_client: LLMClient

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=8192,
            num_output=2048,
            model_name="holocron-groq",
            is_chat_model=False,
        )

    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        text = await self.inner_client.complete_text(prompt)
        return CompletionResponse(text=text)

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        # CompactAndRefine.synthesize() is async-first when called via asynthesize,
        # but the sync path may still be exercised by tests or library internals.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        if loop.is_running():
            # Defensive: this shouldn't happen in our request path because we use
            # asynthesize(), but if it does, surface the misuse clearly.
            raise RuntimeError("HolocronGroqLLM.complete() called from a running event loop; use acomplete()")
        return loop.run_until_complete(self.acomplete(prompt, **kwargs))

    async def achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        # CompactAndRefine doesn't use chat; provide a defensive default.
        prompt = "\n".join(m.content or "" for m in messages)
        completion = await self.acomplete(prompt, **kwargs)
        return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=completion.text))

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.achat(messages, **kwargs))

    async def astream_complete(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError("HolocronGroqLLM does not support streaming")

    def stream_complete(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError("HolocronGroqLLM does not support streaming")

    async def astream_chat(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError("HolocronGroqLLM does not support streaming")

    def stream_chat(self, *args: Any, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError("HolocronGroqLLM does not support streaming")
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_groq_llm_adapter.py -v
```

Expected: 3 passed.

### Step 2.3: TDD — `generate_answer` uses `CompactAndRefine.asynthesize`

- [ ] **Write the failing test in `backend/tests/test_answer_generation_synthesizer.py`:**

```python
import uuid
import pytest

from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import FakeLLMClient
from app.services.retrieval import RetrievalResult


def make_result(idx: int, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=f"Doc {idx}",
        classification="public",
        department="hr",
        effective_date=__import__("datetime").date(2024, 1, 1),
        snippet=text,
        lineage_id=uuid.uuid4(),
        entities=tuple(),
    )


@pytest.mark.asyncio
async def test_generate_answer_uses_synthesizer_path():
    """End-to-end: CompactAndRefine.asynthesize through HolocronGroqLLM(Fake).

    The fake returns a fixed string; we verify the output passes through and
    citations are parsed from the [1] marker the prompt encourages.
    """
    chunks = [make_result(1, "HR runs the office."), make_result(2, "HR sets dress code.")]
    fake = FakeLLMClient(text_responses=["HR runs the office and sets dress code [1][2]."])

    result = await generate_answer(
        query="Who runs HR?",
        chunks=chunks,
        conflicts=[],
        llm=fake,
    )

    assert "HR runs the office and sets dress code" in result.text
    assert len(result.cited_chunk_ids) == 2
    assert fake.calls_text  # the synthesizer made at least one call


@pytest.mark.asyncio
async def test_generate_answer_empty_chunks_returns_fallback():
    fake = FakeLLMClient()  # should never be called
    result = await generate_answer(query="anything", chunks=[], conflicts=[], llm=fake)
    assert "no relevant information" in result.text.lower()
    assert result.cited_chunk_ids == []
    assert fake.calls_text == []
```

- [ ] **Run — verify FAIL:** the existing pattern-only implementation passes the first test but the assertion about `fake.calls_text` may be off-by-one. The second test should already pass. Re-running confirms.

```bash
pytest tests/test_answer_generation_synthesizer.py -v
```

### Step 2.4: Replace pattern-only implementation with `CompactAndRefine`

- [ ] **In `backend/app/services/answer_generation/__init__.py`,** keep `AnswerWithCitations`, `Position`, `Conflict` types but rewrite the `generate_answer` orchestrator:

```python
from __future__ import annotations

from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.prompts import PromptTemplate

from app.services.answer_generation.citations import parse_citation_markers
from app.services.answer_generation.groq_llm_adapter import HolocronGroqLLM
from app.services.answer_generation.llm_client import LLMClient, LLMUnavailable
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    REFINE_TEMPLATE_STR,
    render_conflicts_block,
)
from app.services.retrieval import RetrievalResult


async def generate_answer(
    *,
    query: str,
    chunks: list[RetrievalResult],
    conflicts: list,
    llm: LLMClient,
) -> AnswerWithCitations:
    if not chunks:
        return AnswerWithCitations(
            text="No relevant information was found in the available sources.",
            cited_chunk_ids=[],
            conflicts=[],
        )

    conflicts_block = render_conflicts_block(conflicts, chunks)
    text_qa_template = PromptTemplate(
        ANSWER_TEMPLATE_STR.replace("{conflicts_block}", conflicts_block)
    )
    refine_template = PromptTemplate(
        REFINE_TEMPLATE_STR.replace("{conflicts_block}", conflicts_block)
    )

    adapter = HolocronGroqLLM(inner_client=llm)
    synthesizer = CompactAndRefine(
        llm=adapter,
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        streaming=False,
    )

    nodes = [
        NodeWithScore(
            node=TextNode(text=f"[{i}] {chunk.snippet}", id_=str(chunk.chunk_id)),
            score=1.0,
        )
        for i, chunk in enumerate(chunks, start=1)
    ]

    try:
        response = await synthesizer.asynthesize(query=query, nodes=nodes)
    except LLMUnavailable:
        raise
    except Exception as e:
        raise LLMUnavailable(f"synthesizer failed: {e}") from e

    text = response.response or ""
    markers = parse_citation_markers(text, max_marker=len(chunks))
    cited_chunk_ids = [chunks[m - 1].chunk_id for m in markers]

    # Re-assign conflict Position.marker to match final chunk-position index
    for c in conflicts:
        for pos in (c.position_a, c.position_b):
            for i, chunk in enumerate(chunks, start=1):
                if chunk.chunk_id == pos.chunk_id:
                    pos.marker = i
                    break

    return AnswerWithCitations(
        text=text,
        cited_chunk_ids=cited_chunk_ids,
        conflicts=conflicts,
    )
```

- [ ] **Run targeted tests:**

```bash
pytest tests/test_answer_generation.py tests/test_answer_generation_synthesizer.py tests/test_chat_endpoint.py -v
```

Expected: all pass. If `test_answer_generation.py` has assertions about the exact prompt structure the LLM client received, you may need to relax them — `CompactAndRefine` reformats prompts.

### Step 2.5: Run full suite + commit

- [ ] **Run full suite:**

```bash
pytest
```

Expected: ~135 passing (added 5 new tests). If `LLMUnavailable` exception propagation broke anywhere, fix and re-run.

- [ ] **Commit:**

```bash
git add backend/app/services/answer_generation/groq_llm_adapter.py \
        backend/app/services/answer_generation/__init__.py \
        backend/tests/test_groq_llm_adapter.py \
        backend/tests/test_answer_generation_synthesizer.py
git commit -m "feat(answer): wire LlamaIndex CompactAndRefine via thin HolocronGroqLLM adapter"
```

---

## Task 3: Startup warming + `/healthz/ready`

**Files:**
- Create: `backend/app/core/warmup.py`
- Create: `backend/app/api/healthz.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_warmup.py`
- Create: `backend/tests/test_healthz.py`

### Step 3.1: Add `skip_warmup` setting

- [ ] **In `backend/app/core/config.py`, add to the `Settings` class:**

```python
skip_warmup: bool = False
```

(pydantic-settings auto-reads `HOLOCRON_SKIP_WARMUP` env var if the prefix is `HOLOCRON_`. If your existing settings use a different env_prefix, follow that convention.)

### Step 3.2: TDD — `_warm_sync` flips component flags

- [ ] **Write the failing test in `backend/tests/test_warmup.py`:**

```python
import pytest

from app.core import warmup


@pytest.mark.asyncio
async def test_warm_sync_flips_bge_and_spacy_flags(monkeypatch):
    state = warmup.WarmState()
    
    async def fake_warm_bge():
        state.bge_ready = True
    
    async def fake_warm_spacy():
        state.spacy_ready = True
    
    monkeypatch.setattr(warmup, "_warm_bge", fake_warm_bge)
    monkeypatch.setattr(warmup, "_warm_spacy", fake_warm_spacy)
    
    await warmup.warm_sync(state)
    
    assert state.bge_ready is True
    assert state.spacy_ready is True


@pytest.mark.asyncio
async def test_warm_groq_async_is_fire_and_forget(monkeypatch):
    state = warmup.WarmState()
    calls: list[str] = []
    
    async def fake_probe():
        calls.append("probed")
        state.groq_ready = True
    
    monkeypatch.setattr(warmup, "_probe_groq", fake_probe)
    
    task = warmup.warm_groq_async(state)
    await task
    assert calls == ["probed"]
    assert state.groq_ready is True
```

- [ ] **Run — verify FAIL:**

```bash
pytest tests/test_warmup.py -v
```

Expected: `ModuleNotFoundError`.

### Step 3.3: Implement warmup module

- [ ] **Create `backend/app/core/warmup.py`:**

```python
"""Startup warming: load BGE + spaCy synchronously, probe Groq asynchronously.

Lifespan flow (see app/main.py):
    if not settings.skip_warmup:
        await warmup.warm_sync(state)
        asyncio.create_task(warmup.warm_groq_async(state))
    state.ready = True

Each warm function flips one flag on the shared WarmState. /healthz/ready reads
from this state.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class WarmState:
    bge_ready: bool = False
    spacy_ready: bool = False
    groq_ready: bool = False

    @property
    def core_ready(self) -> bool:
        """Sync warmers done — server can answer /chat/ask. Groq probe is best-effort."""
        return self.bge_ready and self.spacy_ready


async def _warm_bge() -> None:
    """Load BGE and run one embed pass to materialize the tensor graph."""
    from app.services.ingestion.embedding_factory import get_default_embedder
    embedder = get_default_embedder()
    # Run blocking work in a thread so the event loop isn't pinned.
    await asyncio.to_thread(embedder.embed, "warmup")


async def _warm_spacy() -> None:
    """Load spaCy default pipeline + parse one doc."""
    from app.services.ingestion.entity_extractor import get_default_extractor
    extractor = get_default_extractor()
    await asyncio.to_thread(extractor.extract, "Warmup of the spaCy pipeline.")


async def _probe_groq() -> None:
    """Best-effort one-call probe so the first /chat/ask doesn't pay TLS setup."""
    from app.services.answer_generation.llm_client import get_default_llm
    try:
        llm = get_default_llm()
        await llm.complete_text("ping")
    except Exception as e:  # noqa: BLE001
        logger.warning("groq warmup probe failed: %s", e)


async def warm_sync(state: WarmState) -> None:
    await _warm_bge()
    state.bge_ready = True
    await _warm_spacy()
    state.spacy_ready = True


async def warm_groq_async(state: WarmState) -> None:
    await _probe_groq()
    state.groq_ready = True
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_warmup.py -v
```

Expected: 2 passed.

### Step 3.4: TDD — `/healthz/ready` returns 503 when not warm, 200 when warm

- [ ] **Write the failing test in `backend/tests/test_healthz.py`:**

```python
import pytest
from httpx import AsyncClient

from app.main import app
from app.core.warmup import WarmState


@pytest.mark.asyncio
async def test_healthz_ready_returns_503_when_not_warm():
    app.state.warm = WarmState()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    assert resp.status_code == 503
    assert resp.json()["ready"] is False
    assert resp.json()["checks"]["bge"] is False
    assert resp.json()["checks"]["spacy"] is False


@pytest.mark.asyncio
async def test_healthz_ready_returns_200_when_core_warm():
    state = WarmState(bge_ready=True, spacy_ready=True)
    app.state.warm = state
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True
```

- [ ] **Run — verify FAIL:** the endpoint doesn't exist yet.

### Step 3.5: Implement `/healthz/ready`

- [ ] **Create `backend/app/api/healthz.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/healthz", tags=["healthz"])


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict:
    state = getattr(request.app.state, "warm", None)
    bge = bool(state and state.bge_ready)
    spacy = bool(state and state.spacy_ready)
    is_ready = bge and spacy
    if not is_ready:
        response.status_code = 503
    return {
        "ready": is_ready,
        "checks": {"bge": bge, "spacy": spacy, "groq": bool(state and state.groq_ready)},
    }
```

### Step 3.6: Wire lifespan in `main.py`

- [ ] **Modify `backend/app/main.py`** — replace the current top-level `app = FastAPI(...)` with a lifespan-based setup:

```python
from contextlib import asynccontextmanager
import asyncio

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.healthz import router as healthz_router
from app.api.retrieval import router as retrieval_router
from app.core.config import get_settings
from app.core.database import get_session
from app.core.warmup import WarmState, warm_sync, warm_groq_async

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = WarmState()
    app.state.warm = state
    if not settings.skip_warmup:
        await warm_sync(state)
        asyncio.create_task(warm_groq_async(state))
    else:
        # Dev mode: declare core ready immediately; first request pays full cost.
        state.bge_ready = True
        state.spacy_ready = True
    yield


app = FastAPI(title="HOLOCRON", version="0.1.0", lifespan=lifespan)

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
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(healthz_router)
```

- [ ] **Run healthz tests:**

```bash
pytest tests/test_healthz.py -v
```

Expected: 2 passed.

- [ ] **Run full suite:**

```bash
pytest
```

Expected: ~139 passing. The lifespan now runs once per `AsyncClient(app=app)`; if any existing test depends on no warming, set `HOLOCRON_SKIP_WARMUP=1` for the test environment in `conftest.py` (recommended — eval and integration tests shouldn't pay BGE warmup):

```python
# in conftest.py, at module top:
os.environ["HOLOCRON_SKIP_WARMUP"] = "1"
```

### Step 3.7: Commit

```bash
git add backend/app/core/warmup.py backend/app/api/healthz.py \
        backend/app/main.py backend/app/core/config.py \
        backend/tests/test_warmup.py backend/tests/test_healthz.py \
        backend/tests/conftest.py
git commit -m "feat(warmup): FastAPI lifespan warming + /healthz/ready endpoint"
```

---

## Task 4: structlog + `correlation_id` binding

**Files:**
- Create: `backend/app/core/logging.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/test_logging.py`
- Create: `backend/tests/test_correlation_middleware.py`

### Step 4.1: Add structlog dep

- [ ] **In `backend/pyproject.toml`, add to `[project].dependencies`:**

```toml
    "structlog>=24.4,<25.0",
    "pyyaml>=6.0,<7.0",   # needed for Task 5 eval harness; install now to bundle
```

- [ ] **Install:**

```bash
cd backend && pip install -e ".[dev]"
```

Expected: `structlog` and `pyyaml` installed.

### Step 4.2: Add `log_pretty` setting

- [ ] **In `backend/app/core/config.py`, add to `Settings`:**

```python
log_pretty: bool = False
```

### Step 4.3: TDD — `configure_logging` renders console vs JSON correctly

- [ ] **Write the failing test in `backend/tests/test_logging.py`:**

```python
import json
import io
import logging

import pytest
import structlog

from app.core.logging import configure_logging


def test_configure_logging_json_mode_outputs_valid_json(capsys):
    configure_logging(pretty=False)
    log = structlog.get_logger()
    log.info("test_event", foo="bar", count=42)
    captured = capsys.readouterr()
    out = captured.out.strip()
    assert out, "expected JSON output on stdout"
    payload = json.loads(out)
    assert payload["event"] == "test_event"
    assert payload["foo"] == "bar"
    assert payload["count"] == 42
    assert "timestamp" in payload


def test_configure_logging_pretty_mode_does_not_emit_json(capsys):
    configure_logging(pretty=True)
    log = structlog.get_logger()
    log.info("pretty_event", foo="bar")
    captured = capsys.readouterr()
    out = captured.out.strip()
    # Console renderer adds ANSI codes; JSON parse must fail.
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert "pretty_event" in out


def test_contextvar_correlation_id_appears_in_json(capsys):
    configure_logging(pretty=False)
    structlog.contextvars.bind_contextvars(correlation_id="abc-123")
    try:
        log = structlog.get_logger()
        log.info("bound_event")
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)
        assert payload["correlation_id"] == "abc-123"
    finally:
        structlog.contextvars.clear_contextvars()
```

- [ ] **Run — verify FAIL:**

```bash
pytest tests/test_logging.py -v
```

Expected: ModuleNotFoundError.

### Step 4.4: Implement `configure_logging`

- [ ] **Create `backend/app/core/logging.py`:**

```python
"""structlog configuration for HOLOCRON.

Two modes controlled by `HOLOCRON_LOG_PRETTY`:
  - unset / false: JSON renderer (prod, eval, demo recording)
  - true: console renderer (local dev)

correlation_id is bound by middleware via structlog.contextvars; every log
record inside a request gets the same id automatically.
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, pretty: bool) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]

    renderer = (
        structlog.dev.ConsoleRenderer(colors=False)
        if pretty
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_logging.py -v
```

Expected: 3 passed.

### Step 4.5: TDD — correlation-id middleware

- [ ] **Write the failing test in `backend/tests/test_correlation_middleware.py`:**

```python
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_correlation_id_round_trips_when_provided():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready", headers={"x-correlation-id": "manual-id-123"})
    assert resp.headers.get("x-correlation-id") == "manual-id-123"


@pytest.mark.asyncio
async def test_correlation_id_generated_when_absent():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    cid = resp.headers.get("x-correlation-id")
    assert cid
    # UUID4 string length is 36
    assert len(cid) == 36
```

- [ ] **Run — verify FAIL:**

```bash
pytest tests/test_correlation_middleware.py -v
```

Expected: AssertionError on missing header.

### Step 4.6: Wire middleware + configure_logging in main.py

- [ ] **In `backend/app/main.py`, add the import + middleware + log config.** After the `lifespan` function and before `app = FastAPI(...)`:

```python
import uuid
import structlog

from app.core.logging import configure_logging

configure_logging(pretty=settings.log_pretty)
```

After the `CORSMiddleware` block, add:

```python
@app.middleware("http")
async def correlation_id_middleware(request, call_next):
    cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    try:
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        return response
    finally:
        structlog.contextvars.clear_contextvars()
```

### Step 4.7: Thread middleware-generated `correlation_id` into `/chat/ask` audit

The middleware-generated id should be the SAME id used for `audit_events.correlation_id`. Read it from the request inside `post_ask`.

- [ ] **In `backend/app/api/chat.py`, replace the standalone `correlation_id = uuid.uuid4()` from Task 1 Step 1.5 with:**

```python
correlation_id = uuid.UUID(request.headers.get("x-correlation-id"))
```

And add `request: Request` to the `post_ask` signature (import `from fastapi import Request`). This guarantees the audit row's `correlation_id` matches the response header, which matches every log line emitted during the request.

- [ ] **Run middleware test + chat tests:**

```bash
pytest tests/test_correlation_middleware.py tests/test_chat_endpoint.py -v
```

Expected: all pass.

### Step 4.8: Migrate backend modules from `logging.getLogger` to `structlog.get_logger`

- [ ] **Find sites:**

```bash
grep -rn "logging.getLogger\|import logging" backend/app
```

For each module that calls `logging.getLogger(__name__)`, replace with:

```python
import structlog
logger = structlog.get_logger(__name__)
```

Don't change modules that only declare exceptions or constants. Don't change the warmup module — its `logger.warning` was scoped narrowly and works either way; if you do change it, the call site stays `logger.warning("groq warmup probe failed: %s", e)` — structlog accepts the same `%s` placeholder.

- [ ] **Run full suite:**

```bash
pytest
```

Expected: ~141 passing. If `caplog` fixtures are used anywhere in existing tests, they may need to be replaced with structlog's `capture_logs` helper. Search for `caplog`:

```bash
grep -rn "caplog" backend/tests
```

If any matches: update those tests to use `structlog.testing.capture_logs()`. Phase C completion record states no current tests assert on log content, so this should be zero hits.

### Step 4.9: Commit

```bash
git add backend/pyproject.toml backend/app/core/logging.py backend/app/core/config.py \
        backend/app/main.py backend/app/api/chat.py \
        backend/tests/test_logging.py backend/tests/test_correlation_middleware.py \
        backend/app  # picks up any logger migrations
git commit -m "feat(logging): structlog with JSON/console mode + correlation_id middleware"
```

---

## Task 5: Evaluation harness

**Files:**
- Create: `backend/eval/__init__.py`
- Create: `backend/eval/golden_set.yaml`
- Create: `backend/eval/runner.py`
- Create: `backend/eval/scorer.py`
- Create: `backend/eval/report.py`
- Create: `backend/eval/prompts.py`
- Create: `backend/eval/.gitignore`
- Create: `backend/eval/reports/.gitkeep`
- Create: `Makefile` (at repo root if missing)
- Create: `backend/tests/test_eval_scorer.py`
- Create: `backend/tests/test_eval_runner.py`
- Create: `backend/tests/test_eval_report.py`

### Step 5.1: Skeleton package + gitignore

- [ ] **Create `backend/eval/__init__.py`** (empty file).
- [ ] **Create `backend/eval/.gitignore`:**

```
.cache/
*.tmp
```

- [ ] **Create `backend/eval/reports/.gitkeep`** (empty file; ensures the directory survives in git).

### Step 5.2: TDD — pure scoring functions

The `eval` package sits at `backend/eval/`, sibling to `backend/app/`. Tests import as `from eval.scorer import ...`. Make sure pytest picks up the `eval` package by adding to `backend/pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
pythonpath = ["."]
```

(`backend/` already on rootdir; adding `.` keeps `eval` and `app` both importable.)

- [ ] **Write the failing test in `backend/tests/test_eval_scorer.py`:**

```python
import pytest

from eval.scorer import (
    score_retrieval_hit_rate,
    score_refusal_correctness,
    score_conflict_surfacing,
)


def test_retrieval_hit_rate_all_expected_lineages_present():
    expected = ["employee-handbook", "management-conduct-supplement"]
    retrieved_lineages = ["employee-handbook", "management-conduct-supplement", "other"]
    assert score_retrieval_hit_rate(expected, retrieved_lineages) == 1.0


def test_retrieval_hit_rate_half_present():
    expected = ["a", "b"]
    retrieved = ["a", "x"]
    assert score_retrieval_hit_rate(expected, retrieved) == 0.5


def test_retrieval_hit_rate_none_present():
    assert score_retrieval_hit_rate(["a"], []) == 0.0


def test_retrieval_hit_rate_empty_expected_returns_one():
    """No expectations = trivially satisfied. Used for refusal-category rows."""
    assert score_retrieval_hit_rate([], ["anything"]) == 1.0


def test_refusal_correctness_expected_and_got():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=3, min_withheld=1) == 1.0


def test_refusal_correctness_expected_no_min():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=0, min_withheld=None) == 1.0


def test_refusal_correctness_expected_min_not_met():
    assert score_refusal_correctness(expected=True, got=True, withheld_count=1, min_withheld=3) == 0.0


def test_refusal_correctness_unexpected_but_got_one():
    assert score_refusal_correctness(expected=False, got=True, withheld_count=0, min_withheld=None) == 0.0


def test_refusal_correctness_expected_but_missing():
    assert score_refusal_correctness(expected=True, got=False, withheld_count=0, min_withheld=None) == 0.0


def test_refusal_correctness_neither_expected_nor_got():
    assert score_refusal_correctness(expected=False, got=False, withheld_count=0, min_withheld=None) == 1.0


def test_conflict_surfacing_match_substring():
    conflicts = [{"subject": "off-duty insignia and accessory standards"}]
    keywords = ["insignia", "off-duty"]
    assert score_conflict_surfacing(conflicts, keywords) == 1.0


def test_conflict_surfacing_no_match():
    conflicts = [{"subject": "completely unrelated"}]
    keywords = ["insignia"]
    assert score_conflict_surfacing(conflicts, keywords) == 0.0


def test_conflict_surfacing_no_keywords_no_conflicts():
    assert score_conflict_surfacing([], []) == 1.0


def test_conflict_surfacing_expected_keywords_but_no_conflicts_returned():
    assert score_conflict_surfacing([], ["insignia"]) == 0.0
```

- [ ] **Run — verify FAIL:**

```bash
cd backend && pytest tests/test_eval_scorer.py -v
```

Expected: ModuleNotFoundError.

### Step 5.3: Implement scorers

- [ ] **Create `backend/eval/scorer.py`:**

```python
"""Pure scoring functions for the eval harness.

Three are fully deterministic (retrieval, refusal, conflict). The fourth axis
— citation accuracy — needs an LLM and lives in `runner.py` because it has I/O.
"""
from __future__ import annotations

from typing import Sequence


def score_retrieval_hit_rate(
    expected_lineages: Sequence[str], retrieved_lineages: Sequence[str]
) -> float:
    if not expected_lineages:
        return 1.0
    retrieved_set = set(retrieved_lineages)
    hits = sum(1 for l in expected_lineages if l in retrieved_set)
    return hits / len(expected_lineages)


def score_refusal_correctness(
    *, expected: bool, got: bool, withheld_count: int, min_withheld: int | None
) -> float:
    if expected != got:
        return 0.0
    if not expected:
        # Both False: correctly answered, no over-refusal.
        return 1.0
    # Both True: refused as expected. Check min_withheld if specified.
    if min_withheld is not None and withheld_count < min_withheld:
        return 0.0
    return 1.0


def score_conflict_surfacing(
    conflicts: Sequence[dict], expected_keywords: Sequence[str]
) -> float:
    if not expected_keywords:
        return 1.0 if not conflicts else 1.0  # no expectation = pass either way
    for c in conflicts:
        subject = (c.get("subject") or "").lower()
        if any(kw.lower() in subject for kw in expected_keywords):
            return 1.0
    return 0.0
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_eval_scorer.py -v
```

Expected: 14 passed.

### Step 5.4: Write the LLM-judge prompt

- [ ] **Create `backend/eval/prompts.py`:**

```python
"""LLM-as-judge prompt for citation accuracy."""

CITATION_JUDGE_PROMPT = """You are an evaluation judge. Given a question, an answer
with inline citation markers like [1], [2], and the source snippets those markers
refer to, decide whether the citations are appropriate.

Score 1.0 if every cited snippet directly supports the sentence containing its
marker. Score 0.0 if any cited snippet is unrelated or contradicts the sentence.
Use intermediate values (0.5) when citations are partially supported.

Reply ONLY with JSON: {{"score": <float in [0,1]>, "reason": "<one short sentence>"}}

QUESTION: {question}

ANSWER: {answer}

CITED SNIPPETS:
{snippets}
"""
```

### Step 5.5: TDD — runner end-to-end against a mocked client

- [ ] **Write the failing test in `backend/tests/test_eval_runner.py`:**

```python
import pytest

from eval.runner import EvalQuestion, run_single_question, RetrievalResponse, ChatResponse


class FakeApi:
    def __init__(self):
        self.retrieval_response = RetrievalResponse(
            retrieved_lineages=["employee-handbook"],
            refused=False,
            withheld_count=0,
        )
        self.chat_response = ChatResponse(
            retrieved_lineages=["employee-handbook"],
            refused=False,
            withheld_count=0,
            conflicts=[],
            answer="HR runs the office [1].",
            cited_snippets=[{"marker": 1, "snippet": "HR runs the office."}],
        )
        self.citation_score = 1.0

    async def search(self, *, question: str, as_user: str):
        return self.retrieval_response

    async def chat(self, *, question: str, as_user: str):
        return self.chat_response

    async def judge_citation(self, *, question, answer, snippets):
        return self.citation_score


@pytest.mark.asyncio
async def test_run_single_lookup_question_passes_all_axes():
    q = EvalQuestion(
        id="dress-code-1",
        category="lookup",
        as_user="employee.security",
        question="Who runs HR?",
        expected={
            "must_refuse": False,
            "must_cite_lineages": ["employee-handbook"],
        },
    )
    api = FakeApi()
    result = await run_single_question(q, api)

    assert result.id == "dress-code-1"
    assert result.scores["retrieval"] == 1.0
    assert result.scores["refusal"] == 1.0
    assert result.scores["citation"] == 1.0


@pytest.mark.asyncio
async def test_run_single_refusal_question_skips_retrieval_axis():
    q = EvalQuestion(
        id="refusal-1",
        category="refusal",
        as_user="employee.security",
        question="What's the executive search protocol?",
        expected={"must_refuse": True, "refusal_min_withheld": 1, "must_cite_lineages": []},
    )
    api = FakeApi()
    api.chat_response = ChatResponse(
        retrieved_lineages=[],
        refused=True,
        withheld_count=2,
        conflicts=[],
        answer="",
        cited_snippets=[],
    )
    result = await run_single_question(q, api)
    assert result.scores["refusal"] == 1.0
    assert "retrieval" not in result.scores or result.scores["retrieval"] == 1.0
```

- [ ] **Run — verify FAIL:**

```bash
pytest tests/test_eval_runner.py -v
```

Expected: ModuleNotFoundError.

### Step 5.6: Implement runner

- [ ] **Create `backend/eval/runner.py`:**

```python
"""Eval orchestrator: load YAML → run two passes per question → score → write report.

Public entry point: `python -m eval.runner` or `make eval` from repo root.

Architecture:
  - HolocronApiClient calls /retrieval/search and /chat/ask via httpx
  - JudgeClient calls Groq directly via the existing GroqLLMClient
  - scorer.* functions compute deterministic axes
  - run_single_question is the unit of work; pure I/O against the api client
  - run_all collects QuestionResult dataclasses for report.py
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from eval.prompts import CITATION_JUDGE_PROMPT
from eval.scorer import (
    score_conflict_surfacing,
    score_refusal_correctness,
    score_retrieval_hit_rate,
)


# ---- Data shapes ----

@dataclass
class EvalQuestion:
    id: str
    category: str
    as_user: str
    question: str
    expected: dict[str, Any]


@dataclass
class RetrievalResponse:
    retrieved_lineages: list[str]
    refused: bool
    withheld_count: int


@dataclass
class ChatResponse:
    retrieved_lineages: list[str]
    refused: bool
    withheld_count: int
    conflicts: list[dict]
    answer: str
    cited_snippets: list[dict]


@dataclass
class QuestionResult:
    id: str
    category: str
    scores: dict[str, float] = field(default_factory=dict)
    passed: bool = False
    notes: str = ""


# ---- HTTP client ----

class HolocronApiClient:
    """Logs in once per as_user, caches cookies, calls the two endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._cookies_by_user: dict[str, dict] = {}
        self._client = httpx.AsyncClient(timeout=120.0)

    async def _login(self, username: str) -> dict:
        if username in self._cookies_by_user:
            return self._cookies_by_user[username]
        resp = await self._client.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": "imperial-march"},
        )
        resp.raise_for_status()
        cookies = dict(resp.cookies)
        self._cookies_by_user[username] = cookies
        return cookies

    async def search(self, *, question: str, as_user: str) -> RetrievalResponse:
        cookies = await self._login(as_user)
        resp = await self._client.post(
            f"{self.base_url}/retrieval/search",
            json={"query": question, "top_k": 6},
            cookies=cookies,
        )
        resp.raise_for_status()
        body = resp.json()
        retrieved_lineages = [c["lineage_id"] for c in body.get("results", [])]
        refusal = body.get("refusal")
        return RetrievalResponse(
            retrieved_lineages=retrieved_lineages,
            refused=bool(refusal),
            withheld_count=(refusal or {}).get("withheld_count", 0),
        )

    async def chat(self, *, question: str, as_user: str) -> ChatResponse:
        cookies = await self._login(as_user)
        resp = await self._client.post(
            f"{self.base_url}/chat/ask",
            json={"query": question, "top_k": 6},
            cookies=cookies,
        )
        resp.raise_for_status()
        body = resp.json()
        citations = body.get("citations", [])
        retrieved_lineages = [c.get("lineage_id", "") for c in citations]
        refusal = body.get("refusal")
        return ChatResponse(
            retrieved_lineages=retrieved_lineages,
            refused=bool(refusal),
            withheld_count=(refusal or {}).get("withheld_count", 0),
            conflicts=body.get("conflicts", []),
            answer=body.get("answer", {}).get("text", ""),
            cited_snippets=[
                {"marker": c["marker"], "snippet": c["snippet"]} for c in citations
            ],
        )

    async def judge_citation(self, *, question: str, answer: str, snippets: list[dict]) -> float:
        if not snippets:
            return 1.0
        from app.services.answer_generation.llm_client import get_default_llm
        llm = get_default_llm()
        snippets_block = "\n".join(f"[{s['marker']}] {s['snippet']}" for s in snippets)
        prompt = CITATION_JUDGE_PROMPT.format(
            question=question, answer=answer, snippets=snippets_block
        )
        result = await llm.complete_json(prompt)
        return float(result.get("score", 0.0))

    async def close(self) -> None:
        await self._client.aclose()


# ---- Per-question execution ----

async def run_single_question(q: EvalQuestion, api) -> QuestionResult:
    result = QuestionResult(id=q.id, category=q.category)
    expected = q.expected

    if q.category == "refusal":
        # Only full-stack pass; no retrieval expectation.
        chat = await api.chat(question=q.question, as_user=q.as_user)
        result.scores["refusal"] = score_refusal_correctness(
            expected=bool(expected.get("must_refuse")),
            got=chat.refused,
            withheld_count=chat.withheld_count,
            min_withheld=expected.get("refusal_min_withheld"),
        )
    else:
        # Two passes for non-refusal categories.
        retrieval = await api.search(question=q.question, as_user=q.as_user)
        chat = await api.chat(question=q.question, as_user=q.as_user)
        result.scores["retrieval"] = score_retrieval_hit_rate(
            expected.get("must_cite_lineages", []),
            retrieval.retrieved_lineages,
        )
        result.scores["refusal"] = score_refusal_correctness(
            expected=bool(expected.get("must_refuse")),
            got=chat.refused,
            withheld_count=chat.withheld_count,
            min_withheld=expected.get("refusal_min_withheld"),
        )
        if q.category in ("conflict", "cross_department"):
            result.scores["conflict"] = score_conflict_surfacing(
                chat.conflicts, expected.get("conflict_subject_keywords", []),
            )
        # Citation judge (LLM-as-judge)
        result.scores["citation"] = await api.judge_citation(
            question=q.question, answer=chat.answer, snippets=chat.cited_snippets,
        )

    result.passed = all(s >= 0.5 for s in result.scores.values())
    return result


# ---- Top-level orchestration ----

def load_golden_set(path: Path) -> list[EvalQuestion]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [EvalQuestion(**entry) for entry in raw]


async def run_all() -> list[QuestionResult]:
    here = Path(__file__).parent
    questions = load_golden_set(here / "golden_set.yaml")
    api = HolocronApiClient(base_url=os.getenv("HOLOCRON_BASE_URL", "http://localhost:8000"))
    try:
        results: list[QuestionResult] = []
        for q in questions:
            print(f"  → {q.id} ({q.category}, as {q.as_user})", file=sys.stderr)
            results.append(await run_single_question(q, api))
        return results
    finally:
        await api.close()


def main() -> None:
    from eval.report import write_report
    results = asyncio.run(run_all())
    here = Path(__file__).parent
    today = dt.date.today().isoformat()
    md_path = here / "reports" / f"{today}.md"
    json_path = here / "reports" / f"{today}.json"
    write_report(results, md_path=md_path, json_path=json_path, reports_dir=here / "reports")
    passed = sum(1 for r in results if r.passed)
    print(f"\n{passed}/{len(results)} questions passed", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_eval_runner.py -v
```

Expected: 2 passed.

### Step 5.7: TDD — report writer

- [ ] **Write the failing test in `backend/tests/test_eval_report.py`:**

```python
import json
from pathlib import Path

import pytest

from eval.runner import QuestionResult
from eval.report import write_report, diff_runs


def make_result(qid: str, category: str, scores: dict, passed: bool) -> QuestionResult:
    r = QuestionResult(id=qid, category=category)
    r.scores = scores
    r.passed = passed
    return r


def test_write_report_creates_markdown_and_json(tmp_path: Path):
    results = [
        make_result("q1", "lookup", {"retrieval": 1.0, "refusal": 1.0, "citation": 0.9}, True),
        make_result("q2", "refusal", {"refusal": 1.0}, True),
        make_result("q3", "conflict", {"retrieval": 1.0, "refusal": 1.0, "citation": 0.8, "conflict": 0.0}, False),
    ]
    md_path = tmp_path / "x.md"
    json_path = tmp_path / "x.json"
    write_report(results, md_path=md_path, json_path=json_path, reports_dir=tmp_path)

    assert md_path.exists()
    assert json_path.exists()
    payload = json.loads(json_path.read_text())
    assert len(payload["questions"]) == 3
    assert payload["aggregate"]["passed"] == 2
    md = md_path.read_text()
    assert "lookup" in md
    assert "refusal" in md
    assert "conflict" in md


def test_diff_runs_identifies_regressions(tmp_path: Path):
    prev = [make_result("q1", "lookup", {"retrieval": 1.0}, True)]
    curr = [make_result("q1", "lookup", {"retrieval": 0.0}, False)]
    regs, imps = diff_runs(curr_results=curr, prev_results=prev)
    assert regs == ["q1"]
    assert imps == []


def test_diff_runs_identifies_improvements(tmp_path: Path):
    prev = [make_result("q1", "lookup", {"retrieval": 0.0}, False)]
    curr = [make_result("q1", "lookup", {"retrieval": 1.0}, True)]
    regs, imps = diff_runs(curr_results=curr, prev_results=prev)
    assert regs == []
    assert imps == ["q1"]
```

- [ ] **Run — verify FAIL.**

### Step 5.8: Implement report writer

- [ ] **Create `backend/eval/report.py`:**

```python
"""Markdown + JSON scorecard writer for the eval harness."""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from eval.runner import QuestionResult


def _aggregate(results: Iterable[QuestionResult]) -> dict:
    results = list(results)
    by_cat: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    out = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "categories": {},
    }
    for cat, rs in by_cat.items():
        out["categories"][cat] = {
            "n": len(rs),
            "passed": sum(1 for r in rs if r.passed),
        }
    return out


def write_report(
    results: list[QuestionResult],
    *,
    md_path: Path,
    json_path: Path,
    reports_dir: Path,
) -> None:
    agg = _aggregate(results)

    payload = {
        "date": dt.date.today().isoformat(),
        "questions": [asdict(r) for r in results],
        "aggregate": agg,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Diff vs previous run (latest report file alphabetically before today)
    prev_results = _load_prev(reports_dir, exclude=md_path.stem)
    regressions, improvements = diff_runs(results, prev_results) if prev_results else ([], [])

    lines = [f"# HOLOCRON Eval — {payload['date']}", ""]
    lines.append(f"**Total: {agg['passed']}/{agg['total']} passed**\n")
    lines.append("| Category | N | Passed |")
    lines.append("|---|---|---|")
    for cat, c in sorted(agg["categories"].items()):
        lines.append(f"| {cat} | {c['n']} | {c['passed']} |")
    lines.append("")
    if regressions:
        lines.append("## Regressions")
        for qid in regressions:
            lines.append(f"- `{qid}`")
        lines.append("")
    if improvements:
        lines.append("## Improvements")
        for qid in improvements:
            lines.append(f"- `{qid}`")
        lines.append("")
    lines.append("## Per-question")
    lines.append("| ID | Category | Pass | Scores |")
    lines.append("|---|---|---|---|")
    for r in results:
        scores = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(r.scores.items()))
        check = "✓" if r.passed else "✗"
        lines.append(f"| `{r.id}` | {r.category} | {check} | {scores} |")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def diff_runs(
    curr_results: list[QuestionResult],
    prev_results: list[QuestionResult],
) -> tuple[list[str], list[str]]:
    prev_by_id = {r.id: r for r in prev_results}
    regressions: list[str] = []
    improvements: list[str] = []
    for c in curr_results:
        p = prev_by_id.get(c.id)
        if p is None:
            continue
        if p.passed and not c.passed:
            regressions.append(c.id)
        elif not p.passed and c.passed:
            improvements.append(c.id)
    return regressions, improvements


def _load_prev(reports_dir: Path, *, exclude: str) -> list[QuestionResult] | None:
    candidates = sorted(p for p in reports_dir.glob("*.json") if p.stem != exclude)
    if not candidates:
        return None
    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    return [QuestionResult(**q) for q in payload["questions"]]
```

- [ ] **Run — verify PASS:**

```bash
pytest tests/test_eval_report.py -v
```

Expected: 3 passed.

### Step 5.9: Write `golden_set.yaml` (30 entries)

The corpus has known lineage IDs per the seed (`corpus/`). Use lineages from `seed_corpus.py` output. The full set below is illustrative; review actual lineage IDs against `corpus/*/*.md` frontmatter before committing.

- [ ] **Create `backend/eval/golden_set.yaml`** with 30 entries split 12/8/6/4:

```yaml
# 12 lookup
- id: lookup-dress-code-public
  category: lookup
  as_user: employee.security
  question: "What does the employee handbook say about dress code at off-base events?"
  expected:
    must_refuse: false
    must_cite_lineages: [employee-handbook]
    must_flag_conflict: false

- id: lookup-dress-code-supplement
  category: lookup
  as_user: executive.procurement
  question: "What additional dress requirements apply to managers at off-base events?"
  expected:
    must_refuse: false
    must_cite_lineages: [management-conduct-supplement]
    must_flag_conflict: false

- id: lookup-recruitment-public
  category: lookup
  as_user: employee.engineering
  question: "What's the recruitment policy for new hires?"
  expected:
    must_refuse: false
    must_cite_lineages: [recruitment-policy]

- id: lookup-manager-hiring
  category: lookup
  as_user: manager.hr
  question: "What guidelines apply when a manager interviews a candidate?"
  expected:
    must_refuse: false
    must_cite_lineages: [manager-hiring-guidelines]

- id: lookup-it-acceptable-use
  category: lookup
  as_user: employee.engineering
  question: "Am I allowed to install software on my workstation?"
  expected:
    must_refuse: false
    must_cite_lineages: [it-acceptable-use]

- id: lookup-it-access-provisioning
  category: lookup
  as_user: manager.engineering
  question: "How is system access provisioned for a new department member?"
  expected:
    must_refuse: false
    must_cite_lineages: [it-access-provisioning]

- id: lookup-procurement-2024
  category: lookup
  as_user: executive.procurement
  question: "What credit threshold requires executive sign-off for a vendor?"
  expected:
    must_refuse: false
    must_cite_lineages: [procurement-policy]

- id: lookup-onboarding-audit
  category: lookup
  as_user: manager.hr
  question: "How often is the onboarding process audited?"
  expected:
    must_refuse: false
    must_cite_lineages: [onboarding-audit]

- id: lookup-remote-work
  category: lookup
  as_user: employee.engineering
  question: "What are the remote work guidelines?"
  expected:
    must_refuse: false
    must_cite_lineages: [remote-work]

- id: lookup-compensation
  category: lookup
  as_user: manager.hr
  question: "How is salary banding structured?"
  expected:
    must_refuse: false
    must_cite_lineages: [compensation-handbook]

- id: lookup-reactor-public
  category: lookup
  as_user: director.engineering
  question: "What is the standard reactor coolant shutdown sequence?"
  expected:
    must_refuse: false
    must_cite_lineages: [reactor-manual]

- id: lookup-access-audit
  category: lookup
  as_user: director.security
  question: "How often is access reviewed for compliance?"
  expected:
    must_refuse: false
    must_cite_lineages: [access-audit]

# 8 refusal
- id: refusal-dress-code-employee
  category: refusal
  as_user: employee.security
  question: "What's the full management dress code including restricted-tier rules?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-reactor-employee
  category: refusal
  as_user: employee.security
  question: "What is the reactor coolant shutdown procedure?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-incident-response-employee
  category: refusal
  as_user: employee.engineering
  question: "What is the incident response procedure for IT outages?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-exec-search-manager
  category: refusal
  as_user: manager.hr
  question: "What's the executive search protocol?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-insider-threat-employee
  category: refusal
  as_user: employee.engineering
  question: "What insider threat indicators should I watch for?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-exec-fleet-no-hr
  category: refusal
  as_user: executive.fleet
  question: "What additional dress requirements apply to HR managers off-base?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-director-eng-no-hr
  category: refusal
  as_user: director.engineering
  question: "What restricted HR supplement applies to off-base conduct?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

- id: refusal-engineer-no-security
  category: refusal
  as_user: employee.engineering
  question: "What is the access audit process for security clearances?"
  expected:
    must_refuse: true
    refusal_min_withheld: 1
    must_cite_lineages: []

# 6 conflict
- id: conflict-dress-code-2019-vs-2023
  category: conflict
  as_user: executive.procurement
  question: "What's the dress-code policy for off-base events?"
  expected:
    must_refuse: false
    must_cite_lineages: [employee-handbook, management-conduct-supplement]
    must_flag_conflict: true
    conflict_subject_keywords: [insignia, off-duty, dress]

- id: conflict-reactor-shutdown-sequence
  category: conflict
  as_user: director.engineering
  question: "What is the correct coolant shutdown sequence for the reactor?"
  expected:
    must_refuse: false
    must_cite_lineages: [reactor-manual]
    must_flag_conflict: true
    conflict_subject_keywords: [shutdown, sequence, coolant]

- id: conflict-procurement-credit-threshold
  category: conflict
  as_user: executive.procurement
  question: "What credit threshold requires executive sign-off for vendor procurement?"
  expected:
    must_refuse: false
    must_cite_lineages: [procurement-policy]
    must_flag_conflict: true
    conflict_subject_keywords: [credit, threshold, sign-off]

- id: conflict-recruitment-ladder
  category: conflict
  as_user: executive.procurement
  question: "What's the policy for recruiting senior staff?"
  expected:
    must_refuse: false
    must_cite_lineages: [recruitment-policy, manager-hiring-guidelines]
    must_flag_conflict: false

- id: conflict-it-access-ladder
  category: conflict
  as_user: manager.engineering
  question: "How is system access provisioned?"
  expected:
    must_refuse: false
    must_cite_lineages: [it-access-provisioning, it-acceptable-use]
    must_flag_conflict: false

- id: conflict-reactor-employee-refused
  category: conflict
  as_user: director.engineering
  question: "Compare the 2019 and 2023 reactor manuals on shutdown sequencing."
  expected:
    must_refuse: false
    must_cite_lineages: [reactor-manual]
    must_flag_conflict: true
    conflict_subject_keywords: [shutdown, sequence]

# 4 cross_department
- id: xdept-audit-cadence
  category: cross_department
  as_user: director.security
  question: "How often must security audits run? HR and Security disagree — what do the documents say?"
  expected:
    must_refuse: false
    must_cite_lineages: [access-audit, onboarding-audit]
    must_flag_conflict: true
    conflict_subject_keywords: [audit, cadence, frequency]

- id: xdept-incident-response-timing
  category: cross_department
  as_user: director.security
  question: "What's the incident response timing requirement across IT and Security?"
  expected:
    must_refuse: false
    must_cite_lineages: [it-incident-response, insider-threat]
    must_flag_conflict: true
    conflict_subject_keywords: [incident, response, timing]

- id: xdept-onboarding-vs-security
  category: cross_department
  as_user: executive.procurement
  question: "How do HR onboarding and Security access provisioning align?"
  expected:
    must_refuse: false
    must_cite_lineages: [onboarding-audit, access-audit]
    must_flag_conflict: false

- id: xdept-exec-search-protocol
  category: cross_department
  as_user: executive.fleet
  question: "What's the cross-department executive search protocol?"
  expected:
    must_refuse: false
    must_cite_lineages: [executive-search-protocol]
    must_flag_conflict: false
```

> **Lineage names to verify before running:** check each `must_cite_lineages` value against the `lineage_id` field in each `corpus/*/*.md` frontmatter. Mismatched names silently fail retrieval scoring. Run `grep -h "^lineage_id:" corpus/**/*.md | sort -u` to list available lineage IDs.

### Step 5.10: Create root `Makefile` with `eval` target

- [ ] **Create `Makefile` at repo root** (or add `eval:` if Makefile exists):

```makefile
.PHONY: eval eval-retrieval-only

eval:
	cd backend && python -m eval.runner

eval-retrieval-only:
	cd backend && HOLOCRON_EVAL_RETRIEVAL_ONLY=1 python -m eval.runner
```

(The `HOLOCRON_EVAL_RETRIEVAL_ONLY` switch is optional — implement in `runner.run_single_question` if you want a faster smoke. For Phase D, the simple `make eval` is the contract; retrieval-only is convenience.)

### Step 5.11: Run the harness end-to-end against the live system

Prerequisites: backend running on `localhost:8000`, corpus seeded, `GROQ_API_KEY` set in env.

- [ ] **In two terminals:** start the backend and run eval.

Terminal A:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal B (after backend logs say `Application startup complete`):

```bash
make eval
```

Expected: 30 questions stream to stderr, then a scorecard appears at `backend/eval/reports/2026-MM-DD.md`. Aim for ≥ 70% aggregate pass rate on first run. If lower, inspect failing categories: refusal failures often indicate corpus tagging issues; retrieval failures indicate lineage_id mismatches.

- [ ] **Commit the first scorecard:**

```bash
git add backend/eval/reports/2026-MM-DD.md backend/eval/reports/2026-MM-DD.json
git commit -m "eval: first phase-D scorecard (baseline)"
```

### Step 5.12: Run full pytest suite + commit Task 5

- [ ] **Run full suite:**

```bash
cd backend && pytest
```

Expected: ~160 passing (+ 19 new eval tests).

- [ ] **Commit:**

```bash
git add backend/eval Makefile backend/tests/test_eval_scorer.py backend/tests/test_eval_runner.py backend/tests/test_eval_report.py backend/pyproject.toml
git commit -m "feat(eval): harness, golden_set, runner, scorer, report"
```

---

## Task 6: `/admin/audit` viewer

**Files:**
- Create: `backend/app/api/admin.py`
- Modify: `backend/app/repositories/audit_repository.py` (add `list_grouped_by_correlation`)
- Modify: `backend/app/main.py` (register admin_router)
- Create: `backend/tests/test_admin_audit_endpoint.py`
- Create: `frontend/app/admin/layout.tsx`
- Create: `frontend/app/admin/audit/page.tsx`
- Create: `frontend/app/admin/audit/components/AuditFilters.tsx`
- Create: `frontend/app/admin/audit/components/AuditRow.tsx`
- Create: `frontend/app/admin/audit/components/AuditEventDetail.tsx`
- Create: `frontend/lib/audit-api.ts`
- Create: `frontend/lib/types/audit.ts`

### Step 6.1: TDD — `AuditRepository.list_grouped_by_correlation` query

- [ ] **Write failing test in `backend/tests/test_admin_audit_endpoint.py`:**

```python
import uuid
import pytest

from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_list_grouped_returns_one_row_per_correlation_id(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    cid1, cid2 = uuid.uuid4(), uuid.uuid4()

    await repo.insert_query(tenant_id=tenant_id, user_id=user_id, correlation_id=cid1, query_text="q1", retrieved_ids=[])
    await repo.insert_response(tenant_id=tenant_id, user_id=user_id, correlation_id=cid1, response_text="r1", conflicts_found=None, latency_ms=100)
    await repo.insert_query(tenant_id=tenant_id, user_id=user_id, correlation_id=cid2, query_text="q2", retrieved_ids=[])
    await db_session.flush()

    rows, cursor = await repo.list_grouped_by_correlation(tenant_id=tenant_id, limit=50, cursor=None)
    assert len(rows) == 2
    correlation_ids = {r["correlation_id"] for r in rows}
    assert correlation_ids == {cid1, cid2}
    assert all("events" in r for r in rows)


@pytest.mark.asyncio
async def test_list_grouped_filters_by_refusal(db_session, seeded_tenant_user):
    tenant_id, user_id = seeded_tenant_user
    repo = AuditRepository(db_session)
    cid1, cid2 = uuid.uuid4(), uuid.uuid4()
    await repo.insert_query(tenant_id=tenant_id, user_id=user_id, correlation_id=cid1, query_text="q1", retrieved_ids=[])
    await repo.insert_refusal(tenant_id=tenant_id, user_id=user_id, correlation_id=cid1, reference_id="ref", retrieved_ids=[], withheld_ids=[])
    await repo.insert_query(tenant_id=tenant_id, user_id=user_id, correlation_id=cid2, query_text="q2", retrieved_ids=[])
    await db_session.flush()

    rows, _ = await repo.list_grouped_by_correlation(tenant_id=tenant_id, limit=50, cursor=None, has_refusal=True)
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == cid1
```

- [ ] **Run — verify FAIL.**

### Step 6.2: Implement the repository method

- [ ] **In `backend/app/repositories/audit_repository.py`, add:**

```python
import base64
import json
import datetime as dt
from typing import Optional

from sqlalchemy import select


class AuditRepository:
    # ... existing methods ...

    async def list_grouped_by_correlation(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int,
        cursor: Optional[str],
        user_id: Optional[uuid.UUID] = None,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
        has_refusal: Optional[bool] = None,
        has_conflict: Optional[bool] = None,
    ) -> tuple[list[dict], Optional[str]]:
        # Decode cursor
        cursor_dt, cursor_cid = (None, None)
        if cursor:
            decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            cursor_dt = dt.datetime.fromisoformat(decoded["t"])
            cursor_cid = uuid.UUID(decoded["c"])

        # Fetch all matching rows (Phase D scale is small; pagination is per-correlation-group)
        stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(
            AuditEvent.created_at.asc(), AuditEvent.id.asc()
        )
        if user_id:
            stmt = stmt.where(AuditEvent.user_id == user_id)
        if start:
            stmt = stmt.where(AuditEvent.created_at >= start)
        if end:
            stmt = stmt.where(AuditEvent.created_at <= end)

        all_events = (await self._session.execute(stmt)).scalars().all()

        # Group by correlation_id; collect groups ordered by their max created_at desc.
        groups: dict[uuid.UUID, list] = {}
        first_at: dict[uuid.UUID, dt.datetime] = {}
        for e in all_events:
            groups.setdefault(e.correlation_id, []).append(e)
            if e.correlation_id not in first_at or e.created_at < first_at[e.correlation_id]:
                first_at[e.correlation_id] = e.created_at

        sorted_cids = sorted(groups.keys(), key=lambda c: (first_at[c], c), reverse=True)

        # Filter by has_refusal / has_conflict
        def _has_refusal(events: list) -> bool:
            return any(e.event_type == "refusal" for e in events)

        def _has_conflict(events: list) -> bool:
            return any(
                e.conflicts_found and (e.conflicts_found.get("count", 0) > 0)
                for e in events
            )

        if has_refusal is True:
            sorted_cids = [c for c in sorted_cids if _has_refusal(groups[c])]
        elif has_refusal is False:
            sorted_cids = [c for c in sorted_cids if not _has_refusal(groups[c])]
        if has_conflict is True:
            sorted_cids = [c for c in sorted_cids if _has_conflict(groups[c])]
        elif has_conflict is False:
            sorted_cids = [c for c in sorted_cids if not _has_conflict(groups[c])]

        # Cursor seek
        if cursor_dt is not None:
            sorted_cids = [
                c for c in sorted_cids
                if (first_at[c], c) < (cursor_dt, cursor_cid)
            ]

        # Take limit + 1 to know whether there's a next page
        page_cids = sorted_cids[: limit + 1]
        has_more = len(page_cids) > limit
        page_cids = page_cids[:limit]

        rows = []
        for cid in page_cids:
            events = groups[cid]
            latencies = [e.latency_ms for e in events if e.latency_ms is not None]
            user_event_ids = list({e.user_id for e in events})
            rows.append({
                "correlation_id": cid,
                "user_id": user_event_ids[0] if user_event_ids else None,
                "first_event_at": first_at[cid].isoformat(),
                "latency_ms": max(latencies) if latencies else 0,
                "had_refusal": _has_refusal(events),
                "had_conflict": _has_conflict(events),
                "event_count": len(events),
                "events": [self._serialize_event(e) for e in events],
            })

        next_cursor = None
        if has_more and page_cids:
            last_cid = page_cids[-1]
            payload = {"t": first_at[last_cid].isoformat(), "c": str(last_cid)}
            next_cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        return rows, next_cursor

    @staticmethod
    def _serialize_event(e) -> dict:
        return {
            "event_type": e.event_type,
            "query_text": e.query_text,
            "retrieved_ids": [str(x) for x in (e.retrieved_ids or [])],
            "withheld_ids": [str(x) for x in (e.withheld_ids or [])],
            "refusal_ref": e.refusal_ref,
            "response_text": e.response_text,
            "conflicts_found": e.conflicts_found,
            "latency_ms": e.latency_ms,
            "created_at": e.created_at.isoformat(),
        }
```

- [ ] **Run — verify PASS for the repository test:**

```bash
pytest tests/test_admin_audit_endpoint.py -v
```

Expected: 2 passed.

### Step 6.3: TDD — `GET /admin/audit` endpoint

- [ ] **Add a failing endpoint test** in the same `test_admin_audit_endpoint.py`:

```python
@pytest.mark.asyncio
async def test_admin_audit_endpoint_returns_grouped_rows(client, seeded_audit_rows):
    cookies = await login(client, "executive.fleet")
    resp = await client.get("/admin/audit", cookies=cookies)
    assert resp.status_code == 200
    body = resp.json()
    assert "rows" in body
    assert "next_cursor" in body


@pytest.mark.asyncio
async def test_admin_audit_endpoint_role_gated_for_employee(client, seeded_audit_rows):
    cookies = await login(client, "employee.security")
    resp = await client.get("/admin/audit", cookies=cookies)
    assert resp.status_code == 403
```

(`seeded_audit_rows` and `login` are fixtures/helpers to add to `conftest.py`.)

- [ ] **Run — verify FAIL.**

### Step 6.4: Implement the endpoint

- [ ] **Create `backend/app/api/admin.py`:**

```python
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.tenant import get_tenant_context
from app.repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/admin", tags=["admin"])

_ALLOWED_ROLES = {"director", "executive"}


def _require_admin(tenant_ctx) -> None:
    if tenant_ctx.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="admin access required")


@router.get("/audit")
async def get_audit(
    cursor: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    start: dt.datetime | None = Query(default=None),
    end: dt.datetime | None = Query(default=None),
    has_refusal: bool | None = Query(default=None),
    has_conflict: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    tenant_ctx=Depends(get_tenant_context),
) -> dict:
    _require_admin(tenant_ctx)
    repo = AuditRepository(session)
    import uuid as _uuid
    user_uuid = _uuid.UUID(user_id) if user_id else None
    rows, next_cursor = await repo.list_grouped_by_correlation(
        tenant_id=tenant_ctx.tenant_id,
        limit=limit,
        cursor=cursor,
        user_id=user_uuid,
        start=start,
        end=end,
        has_refusal=has_refusal,
        has_conflict=has_conflict,
    )
    # Serialize UUIDs to strings for JSON
    for r in rows:
        r["correlation_id"] = str(r["correlation_id"])
        if r["user_id"]:
            r["user_id"] = str(r["user_id"])
    return {"rows": rows, "next_cursor": next_cursor}
```

- [ ] **Register in `main.py`:**

```python
from app.api.admin import router as admin_router
# ...
app.include_router(admin_router)
```

- [ ] **Run endpoint tests:**

```bash
pytest tests/test_admin_audit_endpoint.py -v
```

Expected: 4 passed (2 repo + 2 endpoint).

### Step 6.5: Frontend types + API wrapper

- [ ] **Create `frontend/lib/types/audit.ts`:**

```typescript
export interface AuditEvent {
  event_type: "query" | "refusal" | "response";
  query_text: string | null;
  retrieved_ids: string[];
  withheld_ids: string[];
  refusal_ref: string | null;
  response_text: string | null;
  conflicts_found: { count: number; subjects: string[] } | null;
  latency_ms: number | null;
  created_at: string;
}

export interface AuditRow {
  correlation_id: string;
  user_id: string | null;
  first_event_at: string;
  latency_ms: number;
  had_refusal: boolean;
  had_conflict: boolean;
  event_count: number;
  events: AuditEvent[];
}

export interface AuditPage {
  rows: AuditRow[];
  next_cursor: string | null;
}

export interface AuditQuery {
  cursor?: string;
  user_id?: string;
  start?: string;
  end?: string;
  has_refusal?: boolean;
  has_conflict?: boolean;
  limit?: number;
}
```

- [ ] **Create `frontend/lib/audit-api.ts`:**

```typescript
import type { AuditPage, AuditQuery } from "@/lib/types/audit";

export async function fetchAuditPage(q: AuditQuery): Promise<AuditPage> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v !== undefined && v !== null) {
      params.set(k, String(v));
    }
  }
  const res = await fetch(`/api/admin/audit?${params}`, { credentials: "include" });
  if (res.status === 403) throw new Error("Forbidden: director/executive role required");
  if (!res.ok) throw new Error(`audit fetch failed: ${res.status}`);
  return res.json();
}
```

(Adjust `/api/admin/audit` to match your frontend proxy convention. If your frontend hits backend directly without a proxy, use the backend base URL.)

### Step 6.6: Admin layout (role gate)

- [ ] **Create `frontend/app/admin/layout.tsx`:**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    async function check() {
      const res = await fetch("/api/auth/me", { credentials: "include" });
      if (res.status !== 200) {
        router.push("/login");
        return;
      }
      const me = await res.json();
      if (me.role === "director" || me.role === "executive") {
        setAllowed(true);
      } else {
        setAllowed(false);
      }
    }
    check();
  }, [router]);

  if (allowed === null) return <div className="p-8">Loading…</div>;
  if (!allowed) return <div className="p-8">Access denied: director or executive role required.</div>;
  return <div className="p-8">{children}</div>;
}
```

### Step 6.7: Audit viewer page + components

- [ ] **Create `frontend/app/admin/audit/page.tsx`:**

```tsx
"use client";

import { useEffect, useState } from "react";

import { AuditFilters } from "./components/AuditFilters";
import { AuditRow } from "./components/AuditRow";
import { fetchAuditPage } from "@/lib/audit-api";
import type { AuditPage, AuditQuery, AuditRow as AuditRowType } from "@/lib/types/audit";

export default function AuditViewerPage() {
  const [filters, setFilters] = useState<AuditQuery>({});
  const [rows, setRows] = useState<AuditRowType[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(reset: boolean) {
    setLoading(true);
    setError(null);
    try {
      const page: AuditPage = await fetchAuditPage({
        ...filters,
        cursor: reset ? undefined : cursor ?? undefined,
      });
      setRows(prev => (reset ? page.rows : [...prev, ...page.rows]));
      setCursor(page.next_cursor);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Audit log</h1>
      <AuditFilters value={filters} onChange={setFilters} />
      {error && <div className="text-red-600">{error}</div>}
      <div className="border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-2">Time</th>
              <th className="text-left p-2">User</th>
              <th className="text-right p-2">Latency</th>
              <th className="text-left p-2">Refusal</th>
              <th className="text-left p-2">Conflict</th>
              <th className="text-right p-2">Events</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => <AuditRow key={r.correlation_id} row={r} />)}
          </tbody>
        </table>
      </div>
      {cursor && (
        <button
          onClick={() => load(false)}
          disabled={loading}
          className="px-3 py-1.5 border rounded hover:bg-gray-50"
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
    </div>
  );
}
```

- [ ] **Create `frontend/app/admin/audit/components/AuditFilters.tsx`:**

```tsx
"use client";

import type { AuditQuery } from "@/lib/types/audit";

export function AuditFilters({
  value,
  onChange,
}: { value: AuditQuery; onChange: (q: AuditQuery) => void }) {
  return (
    <div className="flex flex-wrap gap-3 items-end bg-gray-50 p-3 rounded">
      <label className="text-sm">
        Has refusal
        <select
          value={value.has_refusal === undefined ? "" : String(value.has_refusal)}
          onChange={e => onChange({
            ...value,
            has_refusal: e.target.value === "" ? undefined : e.target.value === "true",
          })}
          className="block border rounded px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        Has conflict
        <select
          value={value.has_conflict === undefined ? "" : String(value.has_conflict)}
          onChange={e => onChange({
            ...value,
            has_conflict: e.target.value === "" ? undefined : e.target.value === "true",
          })}
          className="block border rounded px-2 py-1"
        >
          <option value="">any</option>
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </label>
      <label className="text-sm">
        Start
        <input
          type="datetime-local"
          value={value.start ?? ""}
          onChange={e => onChange({ ...value, start: e.target.value || undefined })}
          className="block border rounded px-2 py-1"
        />
      </label>
      <label className="text-sm">
        End
        <input
          type="datetime-local"
          value={value.end ?? ""}
          onChange={e => onChange({ ...value, end: e.target.value || undefined })}
          className="block border rounded px-2 py-1"
        />
      </label>
      <button onClick={() => onChange({})} className="text-sm underline">clear</button>
    </div>
  );
}
```

- [ ] **Create `frontend/app/admin/audit/components/AuditRow.tsx`:**

```tsx
"use client";

import { useState } from "react";

import { AuditEventDetail } from "./AuditEventDetail";
import type { AuditRow as AuditRowType } from "@/lib/types/audit";

export function AuditRow({ row }: { row: AuditRowType }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr
        className="border-t cursor-pointer hover:bg-gray-50"
        onClick={() => setOpen(o => !o)}
      >
        <td className="p-2 font-mono text-xs">{row.first_event_at.slice(0, 19).replace("T", " ")}</td>
        <td className="p-2">{row.user_id?.slice(0, 8) ?? "—"}</td>
        <td className="p-2 text-right">{row.latency_ms} ms</td>
        <td className="p-2">{row.had_refusal ? "yes" : "—"}</td>
        <td className="p-2">{row.had_conflict ? "yes" : "—"}</td>
        <td className="p-2 text-right">{row.event_count}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={6} className="bg-gray-50 p-3">
            <div className="space-y-2">
              {row.events.map((e, i) => (
                <AuditEventDetail key={i} event={e} />
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
```

- [ ] **Create `frontend/app/admin/audit/components/AuditEventDetail.tsx`:**

```tsx
import type { AuditEvent } from "@/lib/types/audit";

export function AuditEventDetail({ event }: { event: AuditEvent }) {
  return (
    <div className="border rounded p-2 bg-white">
      <div className="flex justify-between text-xs">
        <span className="font-semibold uppercase">{event.event_type}</span>
        <span className="font-mono text-gray-500">{event.created_at}</span>
      </div>
      {event.query_text && (
        <p className="mt-1 text-sm"><span className="font-semibold">Query:</span> {event.query_text}</p>
      )}
      {event.response_text && (
        <p className="mt-1 text-sm"><span className="font-semibold">Response:</span> {event.response_text}</p>
      )}
      {event.refusal_ref && (
        <p className="mt-1 text-sm"><span className="font-semibold">Refusal ref:</span> <code>{event.refusal_ref}</code></p>
      )}
      {event.retrieved_ids.length > 0 && (
        <p className="mt-1 text-xs text-gray-600">
          retrieved: {event.retrieved_ids.length} | withheld: {event.withheld_ids.length}
        </p>
      )}
      {event.conflicts_found && event.conflicts_found.count > 0 && (
        <p className="mt-1 text-xs">
          conflicts: {event.conflicts_found.subjects.join(", ")}
        </p>
      )}
    </div>
  );
}
```

### Step 6.8: Smoke-test in browser

- [ ] **Restart backend, ensure frontend dev server up, log in as `executive.fleet`, navigate to `/admin/audit`.**

Expected: table loads with whatever audit rows exist. Click a row → expand. Filter by `has_refusal=yes` → only refusal rows. Filter by `has_conflict=yes` → only conflict rows.

If the table is empty, run a couple of `/chat/ask` calls first (browser `/chat`) to seed data.

### Step 6.9: Commit Task 6

```bash
git add backend/app/api/admin.py backend/app/repositories/audit_repository.py backend/app/main.py \
        backend/tests/test_admin_audit_endpoint.py backend/tests/conftest.py \
        frontend/app/admin frontend/lib/audit-api.ts frontend/lib/types/audit.ts
git commit -m "feat(admin): /admin/audit viewer with correlation grouping + filters"
```

---

## Task 7: README, 60s demo script, architecture diagram

**Files:**
- Modify: `README.md` (root)
- Create: `docs/architecture/holocron-system.mmd`
- Create: `docs/architecture/holocron-system.svg`

### Step 7.1: Author the architecture mermaid diagram

- [ ] **Create `docs/architecture/holocron-system.mmd`:**

```
graph LR
    subgraph Frontend["Next.js 15 + React 19"]
        Login[/login]
        Chat[/chat]
        Audit[/admin/audit]
    end

    subgraph Backend["FastAPI (Python 3.11)"]
        Auth[auth router]
        Ret[retrieval service<br/>BM25+vector+RRF<br/>RBAC filter]
        Conf[conflict_detection<br/>prefilter + LLM judge]
        Gen[answer_generation<br/>CompactAndRefine]
        AuditR[AuditRepository]
        Warm[lifespan: warm BGE+spaCy]
    end

    subgraph Data["pgvector PG16"]
        Chunks[(chunks<br/>tsvector + HNSW)]
        Docs[(documents)]
        Users[(users + tenants)]
        Events[(audit_events<br/>correlation_id)]
    end

    subgraph External["External"]
        BGE[BGE-base-en-v1.5<br/>local embeddings]
        Groq[Groq llama-3.3-70b<br/>+ llama-3.1-8b fallback]
        Spacy[spaCy en_core_web_sm]
    end

    Login --> Auth
    Chat --> Ret --> Chunks
    Chat --> Conf --> Groq
    Chat --> Gen --> Groq
    Ret -.-> BGE
    Audit --> AuditR --> Events
    Auth --> Users
    Backend --> Warm
```

- [ ] **Render to SVG.** With `mmdc` (mermaid-cli) installed (`pnpm dlx @mermaid-js/mermaid-cli -i docs/architecture/holocron-system.mmd -o docs/architecture/holocron-system.svg`):

```bash
pnpm dlx @mermaid-js/mermaid-cli -i docs/architecture/holocron-system.mmd -o docs/architecture/holocron-system.svg
```

If mmdc is unavailable, paste the .mmd content into <https://mermaid.live>, export SVG, save to `docs/architecture/holocron-system.svg`.

### Step 7.2: Rewrite root README

- [ ] **Update `README.md`** at repo root. Use this structure (adjust if existing content already covers some):

```markdown
# HOLOCRON

> Classification-aware enterprise RAG over a synthetic Galactic Empire corpus.
> Two flagship demos: (1) honest refusal of out-of-clearance content with audit-traceable reference IDs, (2) automatic side-by-side detection of contradictions in retrieved sources.

![Architecture](docs/architecture/holocron-system.svg)

## What this is

HOLOCRON is a portfolio project demonstrating production AI-engineering practice: hybrid RBAC-filtered retrieval (BM25 + pgvector + RRF), heuristic-prefiltered LLM-as-judge conflict detection, grounded `[n]` citations via LlamaIndex `CompactAndRefine`, append-only audit with correlation IDs, and a hand-rolled eval harness with regression diffs.

See [docs/superpowers/specs/2026-06-27-holocron-design.md](docs/superpowers/specs/2026-06-27-holocron-design.md) for the full design rationale.

## Quickstart

Requires: Docker Desktop, Python 3.11, pnpm 11, a Groq API key.

```powershell
# 1. Services
docker compose up -d postgres redis

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
alembic upgrade head
python scripts/seed_users.py    # prints tenant id
python scripts/seed_corpus.py   # ~130s first run (BGE model download)

# 3. Frontend
cd ..\frontend
pnpm install
pnpm approve-builds --all
# Edit .env.local: NEXT_PUBLIC_DEFAULT_TENANT_ID=<tenant id>

# 4. Run
$env:GROQ_API_KEY = "<your-groq-key>"
# Terminal A:
cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000
# Terminal B:
cd frontend; pnpm dev
```

Open <http://localhost:3000>, log in with `executive.procurement` / `imperial-march`.

`GET http://localhost:8000/healthz/ready` returns 200 once BGE + spaCy warming completes (~50s after first docker up).

## 60-second demo script

1. **Login as `executive.procurement`** (Executive tier, HR + Procurement departments).
2. **Ask:** *"What's the dress-code policy for off-base events?"*
   - Expected: answer cites both the Employee Handbook and the Management Conduct Supplement, **conflict card** flags the 2019 vs 2023 disagreement on off-duty insignia.
3. **Logout. Login as `employee.security`** (Employee tier, Security department only).
4. **Ask:** the same question.
   - Expected: answer cites only the public Employee Handbook, **refusal notice** appears: *"N higher-clearance sources may also be relevant. Request access via Reference #..."*
5. **Logout. Login as `director.engineering`.**
6. **Ask:** *"What's the correct coolant shutdown sequence for the reactor?"*
   - Expected: answer cites both 2019 and 2023 Reactor Manuals, **conflict card** flags the procedural disagreement.
7. **Navigate to `/admin/audit`** as `executive.procurement` or `director.engineering`.
   - Expected: rows for all three queries above, grouped by correlation_id. Click any row to expand and see retrieved chunk IDs, withheld chunk IDs, refusal reference, response text, conflict subjects.

## Evaluation

```bash
make eval
```

Runs the 30-question golden set (12 lookup, 8 refusal, 6 conflict, 4 cross-department) against the live system. Writes `backend/eval/reports/YYYY-MM-DD.md` (markdown scorecard + diff vs previous run) and `.json` (machine-readable).

Scoring axes (per spec §7):

- **Retrieval hit-rate** — `must_cite_lineages` ⊆ retrieved lineages. Deterministic.
- **Refusal correctness** — `must_refuse` matches response refusal presence, with optional `refusal_min_withheld` floor. Deterministic.
- **Conflict surfacing** — at least one returned conflict's `subject` substring-matches expected keywords. Deterministic.
- **Citation accuracy** — LLM-as-judge over `(question, answer, cited snippets)` returns a `score ∈ [0, 1]`.

Eval is **local-only** by design; no CI. See [docs/superpowers/specs/2026-06-28-phase-d-eval-audit-polish.md](docs/superpowers/specs/2026-06-28-phase-d-eval-audit-polish.md) §4 decision 3 for rationale.

## Tests

```bash
cd backend && pytest         # default suite, ~155 tests, ~30s
cd backend && pytest -m slow # 4 slow tests (real BGE + spaCy)
```

## Phase status

- Phase A — Foundation ✅
- Phase B — Ingestion + RBAC retrieval ✅
- Phase C — Conflict detection + chat UI ✅
- Phase D — Eval, audit, polish ✅
- Phase 2+ — see [docs/superpowers/specs/2026-06-27-holocron-design.md](docs/superpowers/specs/2026-06-27-holocron-design.md) §10.5 / §10.6
```

(If the existing README already has substantial Phase A/B/C content, preserve it and update only the headers + new sections.)

### Step 7.3: Commit

```bash
git add README.md docs/architecture/holocron-system.mmd docs/architecture/holocron-system.svg
git commit -m "docs: README rewrite + architecture diagram + 60s demo script"
```

---

## Task 8: Manual browser walkthrough + Phase D completion record

**Files:**
- Modify: `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`
- Create: `docs/superpowers/plans/2026-06-28-phase-d-eval-audit-polish-completion.md`
- Modify: `CLAUDE.md`

### Step 8.1: Run the combined Phase B + C + D demo

With backend + frontend running and corpus seeded:

- [ ] **`GET /healthz/ready` returns 200.**
- [ ] **Log in as `executive.procurement`. Dress-code question. Conflict card appears flagging Handbook vs Supplement.**
- [ ] **Inline `[1]`, `[2]` chips scroll to citation cards on click.**
- [ ] **Log in as `employee.security`. Same question. Refusal notice with reference ID appears.**
- [ ] **Log in as `director.engineering`. Reactor coolant question. Conflict card flags 2019 vs 2023 manual disagreement.**
- [ ] **Log in as `employee.security`. Reactor question. Refusal notice appears.**
- [ ] **As `executive.procurement`, navigate to `/admin/audit`. All four queries appear as separate correlation_id rows. Each expands to show 2–3 underlying events. Filtering by `has_refusal=yes` shows only the two refusal rows. Filtering by `has_conflict=yes` shows the two conflict rows.**
- [ ] **Run `make eval`. Confirm scorecard appears at `backend/eval/reports/YYYY-MM-DD.md` and aggregate pass rate ≥ 70%.**
- [ ] **Inspect a log line from the backend stdout. Confirm: JSON when `HOLOCRON_LOG_PRETTY` unset; console-pretty when set; correlation_id appears on every log line inside the `/chat/ask` request.**
- [ ] **Inspect backend response header for `x-correlation-id` — present, UUID format.**
- [ ] **Run `cd frontend && pnpm tsc --noEmit`. Clean.**

### Step 8.2: Update Phase C completion record

- [ ] **In `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`,** tick the unchecked items in the §7.1 demo checklist with a date/comment, e.g.:

```markdown
- [x] `pnpm dev` + `uvicorn` running; navigate to `/chat`. — **Verified in Phase D end-of-phase walkthrough 2026-MM-DD.**
- [x] Demo A — executive view ... — **Verified.**
...
```

### Step 8.3: Write Phase D completion record

- [ ] **Create `docs/superpowers/plans/2026-06-28-phase-d-eval-audit-polish-completion.md`:**

```markdown
# Phase D — Eval, Audit, and Polish: Completion Record

Date verified: 2026-MM-DD
Branch: main

## End-of-phase demo

- [x] All Phase C §7.1 demo checklist items walked and ticked.
- [x] `/healthz/ready` returns 200; first `/chat/ask` after that returns in <5s.
- [x] `/admin/audit` reachable as executive/director; rows grouped by correlation_id; filters work.
- [x] `make eval` produces scorecard at `backend/eval/reports/<date>.md`; aggregate ≥ 70%.
- [x] Backend logs JSON by default; correlation_id on every line inside a request.
- [x] `tsc --noEmit` clean.

## Test results

- Default suite: <N> passed in ~<T>s.
- Slow suite: 4 passed (Phase B BGE + Phase C spaCy).

## Notable deviations

(Fill in any deviations from this plan as they occur; reference commits.)

## Phase D backlog status

Of the original 4-tier backlog, items shipped:
- Task 0 hygiene
- audit correlation_id
- .mappings() migration
- LlamaIndex CompactAndRefine synthesizer
- startup warming + /healthz/ready
- structlog + correlation binding
- eval harness
- /admin/audit viewer
- README + architecture diagram

Deferred (see Phase D spec §3): /admin/documents UI, real-Groq slow test, streaming, arq+Redis worker, general Groq disk cache, SemanticSplitter swap, LRU swap, _sleep shim cleanup, JWT-fuzz hardening, CI eval-smoke.

## MVP shipped

All four phases (A–D) complete. Definition of Done from design spec §13 verified.
```

### Step 8.4: Update CLAUDE.md

- [ ] **In `CLAUDE.md`, update Phase status section:**

```markdown
- **Phase D — Eval + Audit + Polish:** ✅ done (eval harness, audit viewer, startup warming, structlog, README, architecture diagram).
```

Drop the "Phase D backlog" section (or trim to a one-liner pointing at the spec).

- [ ] **Commit:**

```bash
git add docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md \
        docs/superpowers/plans/2026-06-28-phase-d-eval-audit-polish-completion.md \
        CLAUDE.md
git commit -m "docs(phase-d): completion record + Phase C demo verification + CLAUDE.md status"
```

---

## Self-review checklist (post-implementation)

After all 8 tasks ship, verify:

- [ ] `pytest` default suite passes; target ~155 tests.
- [ ] `pytest -m slow` passes (4 slow tests).
- [ ] `pnpm tsc --noEmit` clean from `frontend/`.
- [ ] `make eval` produces a scorecard with aggregate pass rate ≥ 70%.
- [ ] `/healthz/ready` returns 200 once warmed; 503 before.
- [ ] `/admin/audit` reachable as executive/director; rows grouped; filters work.
- [ ] Backend logs JSON to stdout; correlation_id field present on every request-inside log line.
- [ ] `x-correlation-id` header appears on every HTTP response.
- [ ] Architecture SVG renders in README; quickstart works on a fresh clone in under 10 min.
- [ ] All Phase D backlog items in CLAUDE.md (Tier 1–3 + targeted Tier 4) are either done or explicitly deferred per spec §3.

---

## Notes & conventions

- **Migrations:** Alembic uses sequential numeric prefixes (`0001_`, `0002_`). Do not rename or rebase committed migrations.
- **Tests:** TDD throughout; if a test feels hard to write, the design is probably wrong, not the test. The eval harness is the one exception — `golden_set.yaml` is data, not testable by the harness itself.
- **No-op commits:** if any task surface area produces no changes (e.g., Task 0 Step 0.3 if Phase C docs are already accurate), explicitly state "no changes — skip commit" rather than creating an empty commit.
- **Backend tests must keep using `HOLOCRON_SKIP_WARMUP=1`** in `conftest.py` to avoid paying the BGE warm cost per test.
- **The eval harness costs Groq quota.** Run `make eval` deliberately, not in a loop. Cache hits (`eval/.cache/`) are gitignored and re-populated on demand.
- **Manual demo at end is non-negotiable.** Phase C deferred this; Phase D inherits and closes it.
