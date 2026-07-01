# HOLOCRON Phase E — Pass 2 (Hero) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the visual hero pass — two new read-only backend endpoints powering `/me` and `/admin/audit` dashboards, plus every screenshot money-shot from the design handoff: `/login` branded split + demo-account picker, `/me` identity hero + dashboard, `/chat` `CitationCard`/`ConflictCard`/`RefusalNote`/`EmptyState` rewrites + `MessageAssistant` header, `/admin/audit` summary stats + `DataTable` primitive + chip filter bar.

**Architecture:** Backend-first: land the two additive endpoints (`GET /me/recent-queries`, `GET /admin/audit/summary`) so every frontend surface consumes real data on first landing. Then frontend: shared helpers (`lib/demo-questions.ts`, `lib/initials.ts`) → `/chat` hero components (self-contained, screenshot-yielding) → `/me` dashboard → `/login` branded split → `/admin/audit` rebuild → final gates.

**Tech Stack:** Backend: FastAPI 0.115, async SQLAlchemy 2.x, pytest-asyncio · Frontend: Next.js 15 App Router, React 19 RC, TypeScript, Tailwind v3.4 + Phase E semantic tokens (Pass 1), shadcn/ui, lucide-react, Base UI (already installed) — no new deps.

**Design source of truth:** `handoffs/design_handoff_holocron_frontend/README.md` (gitignored, local-only). All oklch values, focused-field ring specs, gradient panel notes, and demo-card layouts live there.

**Verification convention (all tasks):**

- Backend tasks: `python -m pytest -v <path>::<test_name>` for the specific test, then `python -m pytest -v` for the whole suite (must stay green — 181 baseline).
- Frontend tasks: `pnpm build` clean (never `tsc --noEmit` alone), plus a targeted grep sweep when tokens are involved.
- Frontend has no test framework — every task ends with a build + one browser-check step the user runs.

---

## Prerequisites

- [ ] **Confirm you are on the `phase-e-pass-2` branch.**

Run: `git branch --show-current`
Expected: `phase-e-pass-2`

If not on `phase-e-pass-2` (branch was created at session end 2026-07-01 from `main` after Pass 1 merged), run: `git checkout phase-e-pass-2`.

- [ ] **Verify backend test baseline.**

From `backend/` with venv activated:
```
python -m pytest -q
```
Expected: `181 passed` (or higher; Pass 2 must not regress).

- [ ] **Verify frontend build baseline.**

From `frontend/`: `pnpm build`
Expected: build succeeds. Should match the Pass 1 tail (5 routes: `/`, `/admin/audit`, `/chat`, `/login`, `/me`).

---

## Task 1: Backend — `GET /me/recent-queries` endpoint

**Files:**
- Modify: `backend/app/repositories/audit_repository.py`
- Create: `backend/app/api/user.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_recent_queries_endpoint.py`

**Goal:** Add a new repository method `list_recent_queries` and a new router `/me/recent-queries` that returns the current user's last N `query` events (with latency joined from the matching `response` event when available). Any logged-in user reads own data.

- [ ] **Step 1: Write the failing test.**

Create `backend/tests/test_recent_queries_endpoint.py` with:

```python
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.core.security import hash_password
from app.core.warmup import WarmState
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Tenant, User
from app.main import app
from app.repositories.audit_repository import AuditRepository


@pytest_asyncio.fixture
async def some_user(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="manager.hr",
        password_hash=hash_password("imperial-march"),
        role=Role.MANAGER.value,
        max_clearance=ClearanceLevel.RESTRICTED.value,
        departments=["hr"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def other_user(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="employee.security",
        password_hash=hash_password("imperial-march"),
        role=Role.EMPLOYEE.value,
        max_clearance=ClearanceLevel.PUBLIC.value,
        departments=["security"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def client(db_session):
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)

    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login(client: AsyncClient, tenant_id, username) -> None:
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(tenant_id), "username": username, "password": "imperial-march"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_recent_queries_returns_users_own_events_only(
    client, db_session, empire_tenant, some_user, other_user
):
    repo = AuditRepository(db_session)
    # Mine
    my_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=some_user.id, correlation_id=my_cid,
        query_text="my question", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=empire_tenant.id, user_id=some_user.id, correlation_id=my_cid,
        response_text="answered", conflicts_found=None, latency_ms=123,
    )
    # Someone else's
    their_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=other_user.id, correlation_id=their_cid,
        query_text="their question", retrieved_ids=[],
    )
    await db_session.flush()

    await _login(client, empire_tenant.id, some_user.username)
    resp = await client.get("/me/recent-queries")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["query"] == "my question"
    assert item["correlation_id"] == str(my_cid)
    assert item["latency_ms"] == 123
    assert isinstance(item["occurred_at"], str)


@pytest.mark.asyncio
async def test_recent_queries_respects_limit(
    client, db_session, empire_tenant, some_user
):
    repo = AuditRepository(db_session)
    for i in range(8):
        await repo.insert_query(
            tenant_id=empire_tenant.id, user_id=some_user.id,
            correlation_id=uuid.uuid4(),
            query_text=f"q{i}", retrieved_ids=[],
        )
    await db_session.flush()

    await _login(client, empire_tenant.id, some_user.username)
    resp = await client.get("/me/recent-queries?limit=3")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_recent_queries_unauthenticated_is_401(client):
    resp = await client.get("/me/recent-queries")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail.**

From `backend/`: `python -m pytest tests/test_recent_queries_endpoint.py -v`
Expected: All 3 tests FAIL (404 on `/me/recent-queries` — route not registered).

- [ ] **Step 3: Add `list_recent_queries` to `AuditRepository`.**

In `backend/app/repositories/audit_repository.py`, append this method just before `_serialize_event` (after `list_grouped_by_correlation`):

```python
    async def list_recent_queries(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int,
    ) -> list[dict]:
        """Return the user's last N query events with joined response latency
        (null when the request is still in flight or the response event never
        landed). Newest first."""

        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.user_id == user_id,
                AuditEvent.event_type == "query",
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        query_events = (await self._session.execute(stmt)).scalars().all()
        if not query_events:
            return []

        cids = [e.correlation_id for e in query_events]
        lat_stmt = select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.correlation_id.in_(cids),
            AuditEvent.event_type == "response",
        )
        response_events = (await self._session.execute(lat_stmt)).scalars().all()
        latency_by_cid: dict[uuid.UUID, int | None] = {
            e.correlation_id: e.latency_ms for e in response_events
        }

        return [
            {
                "correlation_id": e.correlation_id,
                "query": e.query_text,
                "occurred_at": e.created_at,
                "latency_ms": latency_by_cid.get(e.correlation_id),
            }
            for e in query_events
        ]
```

- [ ] **Step 4: Create the router `backend/app/api/user.py`.**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.tenant import TenantContext, get_tenant_context
from app.repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/recent-queries")
async def recent_queries(
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    repo = AuditRepository(session)
    items = await repo.list_recent_queries(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        limit=limit,
    )
    serialized = []
    for i in items:
        serialized.append({
            "correlation_id": str(i["correlation_id"]),
            "query": i["query"],
            "occurred_at": i["occurred_at"].isoformat(),
            "latency_ms": i["latency_ms"],
        })
    return {"items": serialized}
```

- [ ] **Step 5: Register the router in `main.py`.**

In `backend/app/main.py`, add the import beside the other router imports:

```python
from app.api.user import router as user_router
```

And add the include beside the others (after `app.include_router(admin_router)` is fine):

```python
app.include_router(user_router)
```

- [ ] **Step 6: Run the tests again to verify they pass.**

From `backend/`: `python -m pytest tests/test_recent_queries_endpoint.py -v`
Expected: All 3 PASS.

- [ ] **Step 7: Run the whole backend suite to verify no regression.**

From `backend/`: `python -m pytest -q`
Expected: `184 passed` (181 baseline + 3 new).

- [ ] **Step 8: Commit.**

```
git add backend/app/repositories/audit_repository.py backend/app/api/user.py backend/app/main.py backend/tests/test_recent_queries_endpoint.py
git commit -m "feat(backend): add GET /me/recent-queries endpoint

Returns the current user's last N query events (newest first) with latency
joined from the matching response event. Read-only, own-data-only, any
logged-in role. Powers the /me dashboard's Recent queries panel.

- AuditRepository.list_recent_queries: two-step (query events + response
  latency map by correlation_id).
- New router at backend/app/api/user.py; registered in main.
- 3 new tests covering: own-data-only, limit clamp, 401 unauthenticated."
```

---

## Task 2: Backend — `GET /admin/audit/summary` endpoint

**Files:**
- Modify: `backend/app/repositories/audit_repository.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/tests/test_admin_audit_endpoint.py`

**Goal:** Add `summary_counts` repository method + `GET /admin/audit/summary` endpoint. Role-gated director/executive. Returns today's UTC-boundary counts for queries, refusals, and conflicts (distinct `correlation_id` grouping).

- [ ] **Step 1: Write the failing tests.**

Append to `backend/tests/test_admin_audit_endpoint.py`:

```python
import datetime as dt


@pytest.mark.asyncio
async def test_audit_summary_counts_today_only(
    client, db_session, empire_tenant, admin_user
):
    repo = AuditRepository(db_session)
    # 3 correlation groups today: 2 responses (one with conflict), 1 refusal.
    today_query_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=today_query_cid, query_text="q1", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=today_query_cid, response_text="r1",
        conflicts_found={"count": 1, "subjects": ["x"]}, latency_ms=42,
    )
    today_response_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=today_response_cid, query_text="q2", retrieved_ids=[],
    )
    await repo.insert_response(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=today_response_cid, response_text="r2",
        conflicts_found=None, latency_ms=50,
    )
    refusal_cid = uuid.uuid4()
    await repo.insert_query(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=refusal_cid, query_text="q3", retrieved_ids=[],
    )
    await repo.insert_refusal(
        tenant_id=empire_tenant.id, user_id=admin_user.id,
        correlation_id=refusal_cid, reference_id="ref", retrieved_ids=[],
        withheld_ids=[],
    )
    await db_session.flush()

    await _login(client, empire_tenant.id, admin_user.username)
    resp = await client.get("/admin/audit/summary")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["queries_today"] == 2   # 2 correlation_ids with response
    assert body["refusals_today"] == 1
    assert body["conflicts_today"] == 1


@pytest.mark.asyncio
async def test_audit_summary_role_gated_for_employee(
    client, empire_tenant, non_admin_user
):
    await _login(client, empire_tenant.id, non_admin_user.username)
    resp = await client.get("/admin/audit/summary")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_summary_unauthenticated_is_401(client):
    resp = await client.get("/admin/audit/summary")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail.**

From `backend/`: `python -m pytest tests/test_admin_audit_endpoint.py::test_audit_summary_counts_today_only tests/test_admin_audit_endpoint.py::test_audit_summary_role_gated_for_employee tests/test_admin_audit_endpoint.py::test_audit_summary_unauthenticated_is_401 -v`
Expected: All 3 FAIL (404 on `/admin/audit/summary`).

- [ ] **Step 3: Add `summary_counts` to `AuditRepository`.**

In `backend/app/repositories/audit_repository.py`, add the SQL func import at the top with the other sqlalchemy imports:

```python
from sqlalchemy import func, select
```

Then append this method just before `_serialize_event`:

```python
    async def summary_counts(
        self,
        *,
        tenant_id: uuid.UUID,
        day_utc: _dt.date,
    ) -> dict[str, int]:
        """Count today's audit activity for the summary strip.

        Boundaries are UTC (matches audit_events.created_at). Each count is
        DISTINCT correlation_id under a tenant's row set:
          - queries_today: correlation_ids with a `response` event today
          - refusals_today: correlation_ids with a `refusal` event today
          - conflicts_today: correlation_ids whose response event has
                             conflicts_found.count > 0 today

        Conflicts filter reads the JSON payload in Python (SQL JSON path
        would work but this is the ~1k/day scale documented in
        list_grouped_by_correlation)."""

        start = _dt.datetime.combine(day_utc, _dt.time.min, tzinfo=_dt.timezone.utc)
        end = start + _dt.timedelta(days=1)

        # queries_today: distinct correlation_ids that reached response
        q_stmt = (
            select(func.count(func.distinct(AuditEvent.correlation_id)))
            .where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.event_type == "response",
                AuditEvent.created_at >= start,
                AuditEvent.created_at < end,
            )
        )
        queries_today = (await self._session.execute(q_stmt)).scalar_one()

        # refusals_today: distinct correlation_ids with a refusal event
        r_stmt = (
            select(func.count(func.distinct(AuditEvent.correlation_id)))
            .where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.event_type == "refusal",
                AuditEvent.created_at >= start,
                AuditEvent.created_at < end,
            )
        )
        refusals_today = (await self._session.execute(r_stmt)).scalar_one()

        # conflicts_today: read response events, count those with conflicts.
        c_stmt = select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.event_type == "response",
            AuditEvent.created_at >= start,
            AuditEvent.created_at < end,
        )
        responses = (await self._session.execute(c_stmt)).scalars().all()
        conflicts_today = sum(
            1 for e in responses
            if e.conflicts_found and (e.conflicts_found.get("count", 0) > 0)
        )

        return {
            "queries_today": queries_today,
            "refusals_today": refusals_today,
            "conflicts_today": conflicts_today,
        }
```

- [ ] **Step 4: Add the endpoint to `admin.py`.**

In `backend/app/api/admin.py`, append after the `/audit` route:

```python
@router.get("/audit/summary")
async def audit_summary(
    session: AsyncSession = Depends(get_session),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, int]:
    _require_admin(tenant_ctx)
    repo = AuditRepository(session)
    today = _dt.datetime.now(_dt.timezone.utc).date()
    return await repo.summary_counts(tenant_id=tenant_ctx.tenant_id, day_utc=today)
```

- [ ] **Step 5: Run the tests to verify they pass.**

From `backend/`: `python -m pytest tests/test_admin_audit_endpoint.py -v`
Expected: all tests PASS (existing + 3 new).

- [ ] **Step 6: Run the whole backend suite.**

From `backend/`: `python -m pytest -q`
Expected: `187 passed` (184 after Task 1 + 3 new here).

- [ ] **Step 7: Commit.**

```
git add backend/app/repositories/audit_repository.py backend/app/api/admin.py backend/tests/test_admin_audit_endpoint.py
git commit -m "feat(backend): add GET /admin/audit/summary endpoint

Returns UTC-day counts for queries (correlation_ids that reached response),
refusals, and conflicts (response events whose conflicts_found.count > 0).
Role-gated director/executive. Powers the /admin/audit summary stats row.

- AuditRepository.summary_counts: two SQL COUNT DISTINCT + one Python
  aggregate over response events (JSON payload).
- New endpoint at /admin/audit/summary in existing admin router.
- 3 new tests covering count correctness, role gate, and 401 unauth."
```

---

## Task 3: Frontend — types + API client for the two new endpoints

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`
- Create: `frontend/lib/types/user.ts`
- Create: `frontend/lib/types/audit-summary.ts`

**Goal:** Add TypeScript types and API client methods so Pass 2 components consume real data from Task 1 + Task 2 endpoints.

- [ ] **Step 1: Create `frontend/lib/types/user.ts`.**

```ts
export interface RecentQueryItem {
  correlation_id: string;
  query: string;
  occurred_at: string;
  latency_ms: number | null;
}

export interface RecentQueriesResponse {
  items: RecentQueryItem[];
}
```

- [ ] **Step 2: Create `frontend/lib/types/audit-summary.ts`.**

```ts
export interface AuditSummary {
  queries_today: number;
  refusals_today: number;
  conflicts_today: number;
}
```

- [ ] **Step 3: Extend `frontend/lib/api.ts`.**

Open `frontend/lib/api.ts`. Add imports at the top:

```ts
import type { RecentQueriesResponse } from './types/user';
import type { AuditSummary } from './types/audit-summary';
```

Then extend the `api` object with two new methods (append inside the object literal):

```ts
  recentQueries: (limit = 5) =>
    request<RecentQueriesResponse>(`/me/recent-queries?limit=${limit}`),
  auditSummary: () => request<AuditSummary>('/admin/audit/summary'),
```

- [ ] **Step 4: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Commit.**

```
git add frontend/lib/types/user.ts frontend/lib/types/audit-summary.ts frontend/lib/api.ts
git commit -m "feat(frontend): add types + api client for Phase E endpoints

- lib/types/user.ts: RecentQueryItem, RecentQueriesResponse
- lib/types/audit-summary.ts: AuditSummary
- api.recentQueries(limit), api.auditSummary() methods"
```

---

## Task 4: Frontend — shared helpers (`initials`, `demo-questions`)

**Files:**
- Create: `frontend/lib/initials.ts`
- Modify: `frontend/components/TopNav.tsx`
- Create: `frontend/lib/demo-questions.ts`

**Goal:** Extract the `initials()` function from `TopNav` into a shared lib (so the `AuditRow` primitive in Task 16 can use the same logic), and land the demo-questions content map used by both `/me` (DemoQuestions component) and `/chat` (EmptyState).

- [ ] **Step 1: Create `frontend/lib/initials.ts`.**

```ts
/** Two-letter initials from a dotted username like `executive.fleet` → `EF`. */
export function initials(username: string): string {
  const [head, tail] = username.split(".");
  const first = head?.[0] ?? "";
  const second = tail?.[0] ?? head?.[1] ?? "";
  return (first + second).toUpperCase() || "?";
}
```

- [ ] **Step 2: Refactor `TopNav.tsx` to consume the shared helper.**

Open `frontend/components/TopNav.tsx`. Remove the local `initials` function definition (currently between the `TabDef` interface and the `TopNav` component export). Add the import at the top:

```tsx
import { initials } from "@/lib/initials";
```

Everything else stays.

- [ ] **Step 3: Create `frontend/lib/demo-questions.ts`.**

```ts
export interface DemoQuestion {
  category: string;
  question: string;
  /** lucide-react icon name — resolved via lucide dynamic import at the render site. */
  icon: "shield-check" | "git-compare-arrows" | "lock" | "message-square" | "scroll-text" | "scale";
}

/** Department-keyed suggestions. First department in a user's list wins;
 * fallback used when the department has no map entry. */
const MAP: Record<string, DemoQuestion[]> = {
  hr: [
    { category: "Compliance", question: "What's the dress-code policy for off-base events?", icon: "shield-check" },
    { category: "Compliance", question: "What is the maximum age for recruitment?", icon: "scroll-text" },
    { category: "Compliance", question: "What is the remote-work policy?", icon: "message-square" },
  ],
  engineering: [
    { category: "Conflict detection", question: "What is the reactor coolant shutdown sequence?", icon: "git-compare-arrows" },
    { category: "Reference", question: "What is the reactor emergency protocol?", icon: "scroll-text" },
    { category: "Reference", question: "Who signs off on hardware change orders?", icon: "message-square" },
  ],
  security: [
    { category: "Clearance", question: "What sources are restricted for my clearance?", icon: "lock" },
    { category: "Compliance", question: "What is the insider threat escalation process?", icon: "shield-check" },
    { category: "Compliance", question: "What are the access audit cadences?", icon: "scroll-text" },
  ],
  fleet_operations: [
    { category: "Reference", question: "What is the fleet deployment sign-off chain?", icon: "scroll-text" },
    { category: "Compliance", question: "What sources are restricted for my clearance?", icon: "lock" },
    { category: "Conflict detection", question: "What is the correct coolant shutdown sequence?", icon: "git-compare-arrows" },
  ],
  procurement: [
    { category: "Conflict detection", question: "What is the credit-threshold for supplier orders?", icon: "git-compare-arrows" },
    { category: "Compliance", question: "What is the vendor onboarding sequence?", icon: "scroll-text" },
    { category: "Reference", question: "What is the current procurement approval matrix?", icon: "message-square" },
  ],
  it: [
    { category: "Reference", question: "What is the acceptable-use policy?", icon: "scroll-text" },
    { category: "Compliance", question: "What is the access provisioning workflow?", icon: "shield-check" },
    { category: "Reference", question: "What is the incident response timing?", icon: "message-square" },
  ],
};

const FALLBACK: DemoQuestion[] = [
  { category: "Compliance", question: "What's the dress-code policy for off-base events?", icon: "shield-check" },
  { category: "Conflict detection", question: "What is the correct reactor shutdown sequence?", icon: "git-compare-arrows" },
  { category: "Clearance", question: "What sources are restricted for my clearance?", icon: "lock" },
];

/** Pick a demo question set. Takes the first department that maps; falls back
 * to the generic set. Returns exactly 3 items. */
export function getDemoQuestions(departments: readonly string[]): DemoQuestion[] {
  for (const dept of departments) {
    const q = MAP[dept];
    if (q) return q;
  }
  return FALLBACK;
}
```

- [ ] **Step 4: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Commit.**

```
git add frontend/lib/initials.ts frontend/lib/demo-questions.ts frontend/components/TopNav.tsx
git commit -m "feat(frontend): shared initials + demo-questions helpers

- lib/initials.ts: extract initials() from TopNav (also used by AuditRow
  in Pass 2 Task 16).
- lib/demo-questions.ts: department-keyed DemoQuestion map used by both
  /me DemoQuestions and /chat EmptyState demo cards. Fallback set when
  a department is not in the map."
```

---

## Task 5: `/chat` hero — CitationCard redesign

**Files:**
- Modify: `frontend/app/chat/components/CitationCard.tsx`

**Goal:** Replace the current CitationCard with the hero version: 24×24 filled numbered chip on left, ClearanceBadge right-aligned, mono metadata line, title, snippet, "View source ↗" primary-colored mono at the bottom, hover lift.

- [ ] **Step 1: Overwrite `CitationCard.tsx`.**

Replace the entire file contents with:

```tsx
import { ClearanceBadge } from "@/components/ClearanceBadge";
import { CitationOut } from "@/lib/types/chat";

export function CitationCard({ citation }: { citation: CitationOut }) {
  return (
    <div
      id={`cite-${citation.marker}`}
      className="p-4 border border-border rounded-lg bg-card transition hover:-translate-y-0.5 hover:shadow-md hover:border-border-strong"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="bg-primary text-primary-foreground rounded-md w-6 h-6 grid place-items-center font-mono text-[12px] font-semibold">
          {citation.marker}
        </span>
        <ClearanceBadge classification={citation.classification} />
      </div>
      <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
        {citation.department} · {citation.effective_date}
      </div>
      <div className="text-sm font-semibold mb-1 leading-snug">{citation.document_title}</div>
      <div className="text-[13px] text-muted-foreground leading-snug mb-2">{citation.snippet}</div>
      <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary">
        View source ↗
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/chat/components/CitationCard.tsx
git commit -m "feat(frontend): CitationCard hero redesign

- 24×24 filled numbered chip (bg-primary) on left; ClearanceBadge right.
- Mono metadata line (dept · date) in text-subtle.
- Title 14px/600; snippet 13px/muted; 'View source ↗' primary mono at bottom.
- Hover lift: -translate-y-0.5 + shadow-md + border-strong."
```

---

## Task 6: `/chat` hero — ConflictCard split-diff redesign

**Files:**
- Modify: `frontend/app/chat/components/ConflictCard.tsx`

**Goal:** Replace ConflictCard with the split-diff hero: `bg-conflict-bg` header bar with `GitCompareArrows` icon + subject + "2 SOURCES" pill; CSS-grid body `1fr 60px 1fr` with a center vertical spine + 40px circular "VS" node; footer bar with `Scale` icon + "Holocron's read:" summary line. Mobile stacks the body vertically.

Note: the current backend `ConflictOut.position_a.text` and `position_b.text` are plain strings — no `<mark>` markup for contradicting phrase. Render as-is; phrase highlighting is deferred to Phase F. The footer uses the `subject` field templated.

- [ ] **Step 1: Overwrite `ConflictCard.tsx`.**

Replace the entire file contents with:

```tsx
import { GitCompareArrows, Scale } from "lucide-react";
import { ClearanceBadge } from "@/components/ClearanceBadge";
import type { ConflictOut } from "@/lib/types/chat";

export function ConflictCard({ conflict }: { conflict: ConflictOut }) {
  return (
    <div className="border border-conflict-border rounded-lg overflow-hidden bg-card">
      {/* Header bar */}
      <div className="bg-conflict-bg px-4 py-2.5 flex items-center gap-2 border-b border-conflict-border">
        <GitCompareArrows className="w-4 h-4 text-conflict-foreground" aria-hidden />
        <div className="text-[13px] font-semibold text-conflict-foreground truncate flex-1">
          {conflict.subject}
        </div>
        <span className="px-2 py-0.5 rounded-sm bg-conflict text-conflict-foreground font-mono text-[10px] tracking-[0.08em] uppercase shrink-0">
          2 sources
        </span>
      </div>

      {/* Split-diff body: desktop = 3-col grid with spine; mobile = stacked */}
      <div className="relative grid grid-cols-1 md:grid-cols-[1fr_60px_1fr]">
        <ConflictPanel
          side="a"
          marker={conflict.position_a.marker}
          classification={conflict.position_a.classification}
          text={conflict.position_a.text}
        />
        {/* Spine + VS node (desktop only) */}
        <div className="hidden md:flex relative items-stretch justify-center">
          <div className="w-px bg-conflict-border" aria-hidden />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-card border border-conflict-border shadow-sm grid place-items-center font-mono text-[10px] font-semibold tracking-[0.1em] text-conflict-foreground">
            VS
          </div>
        </div>
        {/* Mobile horizontal divider with VS node */}
        <div className="md:hidden relative flex items-center justify-center py-1 bg-muted/50">
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-px bg-conflict-border" aria-hidden />
          <span className="relative bg-card px-2 rounded-sm border border-conflict-border font-mono text-[10px] font-semibold tracking-[0.1em] text-conflict-foreground">
            VS
          </span>
        </div>
        <ConflictPanel
          side="b"
          marker={conflict.position_b.marker}
          classification={conflict.position_b.classification}
          text={conflict.position_b.text}
          tinted
        />
      </div>

      {/* Footer bar */}
      <div className="bg-muted border-t border-border px-4 py-2.5 flex items-center gap-2">
        <Scale className="w-3.5 h-3.5 text-muted-foreground shrink-0" aria-hidden />
        <div className="text-[12px] text-muted-foreground">
          <span className="font-semibold text-foreground">Holocron&rsquo;s read:</span>{" "}
          The two sources disagree on <span className="italic">{conflict.subject}</span>.
        </div>
      </div>
    </div>
  );
}

function ConflictPanel({
  side,
  marker,
  classification,
  text,
  tinted = false,
}: {
  side: "a" | "b";
  marker: number;
  classification: import("@/lib/types/chat").Clearance;
  text: string;
  tinted?: boolean;
}) {
  return (
    <a
      href={`#cite-${marker}`}
      className={`block p-4 hover:bg-muted transition ${tinted ? "bg-[oklch(0.992_0.004_247)]" : ""}`}
      aria-label={`Jump to citation ${marker} (side ${side})`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="bg-accent text-accent-foreground rounded-sm px-1.5 py-0.5 font-mono text-[11px] font-semibold">
          [{marker}]
        </span>
        <ClearanceBadge classification={classification} />
      </div>
      <div className="text-[13px] text-foreground leading-relaxed">{text}</div>
    </a>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS. The `bg-[oklch(0.992_0.004_247)]` arbitrary value is one of the two spec-sanctioned inline oklch shades — that's fine, don't try to token-ify it.

- [ ] **Step 3: Commit.**

```
git add frontend/app/chat/components/ConflictCard.tsx
git commit -m "feat(frontend): ConflictCard split-diff hero redesign

- Header bar (bg-conflict-bg): GitCompareArrows icon + subject + '2 SOURCES' pill.
- Body: CSS grid 1fr 60px 1fr (mobile: stacks vertically with horizontal
  divider). Center spine + 40px circular 'VS' node.
- Panels: citation chip + ClearanceBadge on top row; text below.
- Right panel tinted oklch(0.992 0.004 247) per handoff.
- Footer bar (bg-muted): Scale icon + 'Holocron's read: subject' templated.
- Contradicting-phrase highlighting (<mark>) is Phase F polish — needs
  the LLM to output structured markup which it doesn't yet."
```

---

## Task 7: `/chat` hero — RefusalNote polish + copy-ref-to-clipboard

**Files:**
- Modify: `frontend/app/chat/components/RefusalNote.tsx`

**Goal:** Replace the current RefusalNote with the hero layout: 3-column grid (icon | text | actions). Left = 40px `bg-accent` circle with Lock icon. Middle = heading + subline. Right = mono ref# + outline "Request access" button that copies the ref# to clipboard.

- [ ] **Step 1: Overwrite `RefusalNote.tsx`.**

```tsx
"use client";

import { useState } from "react";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  const [copied, setCopied] = useState(false);

  async function copyRef() {
    try {
      await navigator.clipboard.writeText(refusal.reference_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard denied — silently no-op (demo build, no toast infrastructure).
    }
  }

  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-4 p-4 bg-muted border border-dashed border-border-strong rounded-lg">
      <div className="w-10 h-10 rounded-full bg-accent text-accent-foreground grid place-items-center shrink-0">
        <Lock className="w-4 h-4" aria-hidden />
      </div>
      <div>
        <div className="text-[13px] font-semibold text-foreground">
          Some matches are above your clearance
        </div>
        <div className="text-[12px] text-muted-foreground">
          {refusal.withheld_count} higher-clearance source
          {refusal.withheld_count === 1 ? "" : "s"} may also be relevant.
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <code className="hidden sm:inline-block bg-card border border-border rounded-sm px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          REF #{refusal.reference_id}
        </code>
        <Button
          variant="outline"
          onClick={copyRef}
          className="text-[12px]"
        >
          {copied ? "Copied ✓" : "Request access"}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/chat/components/RefusalNote.tsx
git commit -m "feat(frontend): RefusalNote hero polish + copy-ref-to-clipboard

- 3-col grid (icon | text | actions).
- Left: 40px bg-accent circle with Lock icon.
- Middle: 'Some matches are above your clearance' heading + N-sources subline.
- Right (hidden on <sm): mono REF #… + 'Request access' outline button that
  writes the ref_id to clipboard (with 1.6s 'Copied ✓' feedback)."
```

---

## Task 8: `/chat` hero — EmptyState component + demo cards

**Files:**
- Create: `frontend/app/chat/components/EmptyState.tsx`

**Goal:** Land the empty-state hero — centered 48px accent tile with Sparkles + heading + subtitle + 3-col demo-question card grid (mobile: 1 col). Demo cards resolve icons from lucide dynamically. Clicking a card calls the provided `onPick(question)` callback (wired to `send()` in Task 9).

Note: the handoff prototype also shows an "input mock" below the demo grid. Skip it — the real `ChatInput` is already rendered by `ChatPage` below the empty state; a mock next to it would be confusing.

- [ ] **Step 1: Create `EmptyState.tsx`.**

```tsx
"use client";

import {
  ArrowRight,
  GitCompareArrows,
  Lock,
  MessageSquare,
  Scale,
  ScrollText,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import type { DemoQuestion } from "@/lib/demo-questions";

const ICONS: Record<DemoQuestion["icon"], LucideIcon> = {
  "shield-check": ShieldCheck,
  "git-compare-arrows": GitCompareArrows,
  lock: Lock,
  "message-square": MessageSquare,
  "scroll-text": ScrollText,
  scale: Scale,
};

export function EmptyState({
  questions,
  onPick,
  disabled,
}: {
  questions: readonly DemoQuestion[];
  onPick: (question: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-3xl text-center">
        <div className="mx-auto mb-4 w-12 h-12 rounded-lg bg-accent text-accent-foreground grid place-items-center">
          <Sparkles className="w-6 h-6" aria-hidden />
        </div>
        <h2 className="text-[23px] font-semibold tracking-[-0.015em] mb-2">
          What can the archive answer for you?
        </h2>
        <p className="text-[13px] text-muted-foreground mb-8">
          Try one of these questions to see clearance-filtered retrieval, citations, and conflict detection in action.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-left">
          {questions.map((q) => {
            const Icon = ICONS[q.icon];
            return (
              <button
                key={q.question}
                type="button"
                disabled={disabled}
                onClick={() => onPick(q.question)}
                className="p-4 bg-card border border-border rounded-lg text-left transition hover:-translate-y-0.5 hover:shadow-md hover:border-border-strong disabled:opacity-50 disabled:pointer-events-none"
              >
                <div className="w-8 h-8 rounded-md bg-accent text-accent-foreground grid place-items-center mb-3">
                  <Icon className="w-4 h-4" aria-hidden />
                </div>
                <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                  {q.category}
                </div>
                <div className="text-[13px] font-medium leading-snug mb-3">{q.question}</div>
                <div className="flex items-center gap-1 text-[11px] font-mono uppercase tracking-[0.08em] text-primary">
                  Try it <ArrowRight className="w-3 h-3" aria-hidden />
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS. (`EmptyState` isn't imported anywhere yet — that happens in Task 9.)

- [ ] **Step 3: Commit.**

```
git add frontend/app/chat/components/EmptyState.tsx
git commit -m "feat(frontend): /chat EmptyState hero component

Centered 48px bg-accent Sparkles tile + heading + subtitle + 3-col demo-
question card grid (mobile: 1 col). Cards render dept-seeded content
from lib/demo-questions; icons resolve via a small lucide map. Cards call
onPick(question) — wired to /chat page's send() in Task 9."
```

---

## Task 9: `/chat` — MessageAssistant header + latency measurement + integration

**Files:**
- Modify: `frontend/app/chat/components/MessageAssistant.tsx`
- Modify: `frontend/app/chat/components/ChatThread.tsx`
- Modify: `frontend/app/chat/page.tsx`

**Goal:** Add the `Sparkles + Holocron + N sources · N conflict · N.Ns` header row at the top of the assistant bubble (per handoff). Latency is measured client-side around the fetch and threaded through the Turn → MessageAssistant. Also swap the current `SUGGESTED` array for the department-seeded EmptyState + support prefill from a `?q=…` query param (used by DemoQuestions in `/me`).

- [ ] **Step 1: Update `MessageAssistant.tsx` — add header row.**

Add `Sparkles` to the lucide imports and accept an optional `latencyMs` prop. Replace the top-level `<div className="bg-card rounded-lg rounded-tl-md p-4 text-sm leading-relaxed">` open-and-first-child region with:

```tsx
import React from "react";
import { Sparkles, TriangleAlert } from "lucide-react";
import { ChatResponse } from "@/lib/types/chat";
import { CitationChip } from "@/components/CitationChip";
import { CitationCard } from "./CitationCard";
import { ConflictCard } from "./ConflictCard";
import { RefusalNote } from "./RefusalNote";

function renderAnswerText(text: string) {
  const parts = text.split(/(\[\d+\])/);
  return parts.map((token, i) => {
    const m = token.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{token}</React.Fragment>;
    const marker = parseInt(m[1], 10);
    return <CitationChip key={i} marker={marker} />;
  });
}

export function MessageAssistant({
  payload,
  latencyMs,
}: {
  payload: ChatResponse;
  latencyMs?: number;
}) {
  const nSources = payload.citations.length;
  const nConflicts = payload.conflicts.length;
  return (
    <div className="self-start w-full max-w-[95%] flex flex-col gap-3">
      <div className="bg-card rounded-lg rounded-tl-md p-4 text-sm leading-relaxed">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-md bg-primary text-primary-foreground grid place-items-center">
            <Sparkles className="w-3.5 h-3.5" aria-hidden />
          </div>
          <div className="text-[13px] font-semibold">Holocron</div>
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground ml-auto">
            {nSources} source{nSources === 1 ? "" : "s"} · {nConflicts} conflict{nConflicts === 1 ? "" : "s"}
            {latencyMs !== undefined ? ` · ${(latencyMs / 1000).toFixed(2)}s` : ""}
          </div>
        </div>
        <div className="leading-relaxed">{renderAnswerText(payload.answer.text)}</div>
      </div>

      {payload.citations.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
            Citations · {payload.citations.length}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {payload.citations.map((c) => (
              <CitationCard key={c.marker} citation={c} />
            ))}
          </div>
        </div>
      )}

      {payload.conflicts.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-red-700 mb-1.5 flex items-center gap-1">
            <TriangleAlert className="w-3 h-3" aria-hidden />
            Conflicts detected · {payload.conflicts.length}
          </div>
          <div className="flex flex-col gap-2">
            {payload.conflicts.map((c, i) => (
              <ConflictCard key={i} conflict={c} />
            ))}
          </div>
        </div>
      )}

      {payload.refusal && <RefusalNote refusal={payload.refusal} />}

      {payload.answer.cited_chunk_ids.length === 0 && payload.citations.length === 0 && (
        <div className="text-[10px] text-subtle italic">
          No citations attached to this answer.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Update `ChatThread.tsx` — thread latency through the assistant Turn.**

Open `frontend/app/chat/components/ChatThread.tsx`. Update the `Turn` type union and the `assistant` case:

```tsx
export type Turn =
  | { kind: "user"; id: string; query: string }
  | { kind: "assistant"; id: string; payload: ChatResponse; latencyMs?: number }
  | { kind: "assistant-pending"; id: string }
  | { kind: "assistant-error"; id: string; message: string; previousQuery: string };
```

And the switch case:

```tsx
          case "assistant":
            return <MessageAssistant key={t.id} payload={t.payload} latencyMs={t.latencyMs} />;
```

- [ ] **Step 3: Update `chat/page.tsx` — measure latency, seed empty state by dept, support `?q=…` prefill.**

Open `frontend/app/chat/page.tsx`. Add imports:

```tsx
import { useSearchParams } from "next/navigation";
import { EmptyState } from "./components/EmptyState";
import { getDemoQuestions } from "@/lib/demo-questions";
```

Delete the `SUGGESTED` constant (it's replaced by `getDemoQuestions(me.departments)`).

Inside `ChatPage`:

Add the search-params hook near the other hooks:

```tsx
  const searchParams = useSearchParams();
```

Add a prefill-once effect after the `useEffect` that scrolls, before `send`:

```tsx
  const prefillOnceRef = useRef(false);
  useEffect(() => {
    if (prefillOnceRef.current || !me) return;
    const q = searchParams.get("q");
    if (q && q.trim()) {
      prefillOnceRef.current = true;
      send(q.trim());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me, searchParams]);
```

Add `useRef` to the `react` import at the top if it's not already there. And note that `send` is defined below — TypeScript may still resolve it because it's a hoisted function declaration... but the current code uses `async function send`, which IS hoisted. Verify at the file level.

Modify `send()` to measure and thread latency:

```tsx
  async function send(query: string) {
    const userTurn: Turn = { kind: "user", id: nextId(), query };
    const pendingTurn: Turn = { kind: "assistant-pending", id: nextId() };
    setTurns((t) => [...t, userTurn, pendingTurn]);
    setSending(true);
    const startedAt = performance.now();
    try {
      const payload = await postChatAsk(query);
      const latencyMs = Math.round(performance.now() - startedAt);
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id
            ? { kind: "assistant", id: x.id, payload, latencyMs }
            : x
        )
      );
    } catch (e) {
      const msg =
        e instanceof LLMUnavailableError
          ? "LLM temporarily unavailable. Please retry."
          : (e as Error).message === "unauthenticated"
          ? "Session expired. Please log in again."
          : "Request failed. Please retry.";
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id
            ? { kind: "assistant-error", id: x.id, message: msg, previousQuery: query }
            : x
        )
      );
      if ((e as Error).message === "unauthenticated") {
        router.replace("/login?next=/chat");
      }
    } finally {
      setSending(false);
    }
  }
```

Replace the empty-state JSX. Find the `turns.length === 0 ?` block and replace the entire ternary branch with:

```tsx
      {turns.length === 0 ? (
        <EmptyState
          questions={getDemoQuestions(me.departments)}
          onPick={send}
          disabled={sending}
        />
      ) : (
        <ChatThread turns={turns} onRetry={(q) => send(q)} />
      )}
```

Remove the `import { ClearanceBadge }` if it's still there (post-Pass-1 the header was removed, so ClearanceBadge should already be gone from chat/page.tsx; if grep says otherwise, remove it now).

- [ ] **Step 4: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Commit.**

```
git add frontend/app/chat/components/MessageAssistant.tsx frontend/app/chat/components/ChatThread.tsx frontend/app/chat/page.tsx
git commit -m "feat(frontend): /chat MessageAssistant header + latency + prefill + dept-seeded empty state

- MessageAssistant: 7×7 primary Sparkles tile + 'Holocron' + mono
  'N sources · N conflict · N.Ns' header row.
- Turn.assistant now carries latencyMs (client-side timing around
  postChatAsk); wired through ChatThread.
- ChatPage: empty state uses <EmptyState/> seeded by user's departments;
  ?q=… query-param prefill triggers send on first mount (used by /me
  DemoQuestions and any deep-link demos)."
```

---

## Task 10: `/me` — RecentQueries component

**Files:**
- Create: `frontend/app/me/components/RecentQueries.tsx`

**Goal:** List of the user's last 5 query events (from `api.recentQueries()`). Each row: mono timestamp + `CornerDownRight` icon + ellipsized query text. Click → navigate to `/chat?q={query}`.

- [ ] **Step 1: Create `RecentQueries.tsx`.**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CornerDownRight, History } from "lucide-react";

import { api } from "@/lib/api";
import type { RecentQueryItem } from "@/lib/types/user";

function relativeTime(iso: string): string {
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const s = Math.max(0, Math.floor(diffMs / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const days = Math.floor(h / 24);
  return `${days}d`;
}

export function RecentQueries() {
  const [items, setItems] = useState<RecentQueryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .recentQueries(5)
      .then((r) => {
        if (!cancelled) setItems(r.items);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <History className="w-4 h-4 text-muted-foreground" aria-hidden />
        <div className="text-[13px] font-semibold">Recent queries</div>
      </div>
      {items === null && !error && (
        <div className="text-[13px] text-muted-foreground">Loading…</div>
      )}
      {error && (
        <div className="text-[13px] text-muted-foreground">
          Couldn&rsquo;t load recent activity.
        </div>
      )}
      {items && items.length === 0 && (
        <div className="text-[13px] text-muted-foreground">
          No queries yet. Try one from the panel on the right.
        </div>
      )}
      {items && items.length > 0 && (
        <ul className="flex flex-col gap-1">
          {items.map((it) => (
            <li key={it.correlation_id}>
              <Link
                href={`/chat?q=${encodeURIComponent(it.query)}`}
                className="group flex items-start gap-2 p-2 -mx-2 rounded-md hover:bg-muted transition"
              >
                <span className="w-12 shrink-0 font-mono text-[11px] text-subtle mt-0.5">
                  {relativeTime(it.occurred_at)}
                </span>
                <CornerDownRight className="w-3.5 h-3.5 text-subtle shrink-0 mt-0.5" aria-hidden />
                <span className="text-[13px] text-foreground truncate group-hover:text-foreground">
                  {it.query}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/me/components/RecentQueries.tsx
git commit -m "feat(frontend): /me RecentQueries component

Fetches last 5 items from /me/recent-queries. Renders relative timestamp
(mono, subtle) + CornerDownRight icon + ellipsized query text. Row click
navigates to /chat?q=… which prefills the chat query via Task 9's search-
param hook."
```

---

## Task 11: `/me` — DemoQuestions component (dashboard variant)

**Files:**
- Create: `frontend/app/me/components/DemoQuestions.tsx`

**Goal:** 3-row list of "Try a demo question" cards seeded by the user's first department. Icon tile + category + question + arrow. Click → navigate to `/chat?q={question}`.

- [ ] **Step 1: Create `DemoQuestions.tsx`.**

```tsx
"use client";

import Link from "next/link";
import {
  ArrowRight,
  GitCompareArrows,
  Lock,
  MessageSquare,
  Scale,
  ScrollText,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { getDemoQuestions, type DemoQuestion } from "@/lib/demo-questions";

const ICONS: Record<DemoQuestion["icon"], LucideIcon> = {
  "shield-check": ShieldCheck,
  "git-compare-arrows": GitCompareArrows,
  lock: Lock,
  "message-square": MessageSquare,
  "scroll-text": ScrollText,
  scale: Scale,
};

export function DemoQuestions({ departments }: { departments: readonly string[] }) {
  const questions = getDemoQuestions(departments);
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-muted-foreground" aria-hidden />
        <div className="text-[13px] font-semibold">Try a demo question</div>
      </div>
      <ul className="flex flex-col gap-1">
        {questions.map((q) => {
          const Icon = ICONS[q.icon];
          return (
            <li key={q.question}>
              <Link
                href={`/chat?q=${encodeURIComponent(q.question)}`}
                className="group flex items-center gap-3 p-2 -mx-2 rounded-md hover:bg-muted hover:translate-x-0.5 transition"
              >
                <div className="w-8 h-8 rounded-md bg-accent text-accent-foreground grid place-items-center shrink-0">
                  <Icon className="w-4 h-4" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle">
                    {q.category}
                  </div>
                  <div className="text-[13px] font-medium truncate">{q.question}</div>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:text-primary" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/me/components/DemoQuestions.tsx
git commit -m "feat(frontend): /me DemoQuestions dashboard component

3-row list of demo questions seeded by user's first department (via
lib/demo-questions.getDemoQuestions). Icon tile + mono category + question
+ ArrowRight. Row click navigates to /chat?q=… which prefills via Task 9."
```

---

## Task 12: `/me` — identity hero + dashboard page composition

**Files:**
- Modify: `frontend/app/me/page.tsx`

**Goal:** Rewrite `/me` as a dashboard: identity hero card (56px gradient avatar, title, tenant subtitle, tenant-logo placeholder tile, 3-col meta grid), actions row (Open chat + View audit log role-gated + Sign out), lower `1fr 1.15fr` grid (RecentQueries | DemoQuestions). Mobile stacks.

- [ ] **Step 1: Overwrite `me/page.tsx`.**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ClearanceBadge } from '@/components/ClearanceBadge';
import { TopNav } from '@/components/TopNav';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { initials } from '@/lib/initials';
import type { UserSummary } from '@/lib/types';

import { DemoQuestions } from './components/DemoQuestions';
import { RecentQueries } from './components/RecentQueries';

function tenantAcronym(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

export default function MePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace('/login'))
      .finally(() => setLoading(false));
  }, [router]);

  async function onLogout() {
    await api.logout();
    router.replace('/login');
  }

  if (loading) return <main className="p-8 text-muted-foreground">Loading…</main>;
  if (!user) return null;

  const isAdmin = user.role === 'director' || user.role === 'executive';

  return (
    <>
      <TopNav user={{ username: user.username, role: user.role, max_clearance: user.max_clearance }} />
      <main className="mx-auto max-w-5xl p-4 sm:p-8 space-y-6">
        {/* Identity hero card */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-start gap-4">
            <div
              className="w-14 h-14 rounded-lg grid place-items-center text-primary-foreground font-mono text-[16px] font-semibold shrink-0"
              style={{
                background:
                  'linear-gradient(135deg, oklch(0.52 0.16 264) 0%, oklch(0.40 0.14 264) 100%)',
              }}
              aria-hidden
            >
              {initials(user.username)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[19px] font-semibold leading-tight truncate">
                {user.tenant.role_label}: {user.username}
              </div>
              <div className="text-[13px] text-muted-foreground">{user.tenant.name}</div>
            </div>
            <div
              className="hidden sm:grid w-12 h-12 rounded-md bg-muted border border-border place-items-center font-mono text-[11px] font-semibold text-muted-foreground shrink-0"
              aria-hidden
            >
              {tenantAcronym(user.tenant.name) || '—'}
            </div>
          </div>

          <div className="h-px bg-border my-5" aria-hidden />

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Max clearance
              </dt>
              <dd>
                <ClearanceBadge classification={user.max_clearance} />
              </dd>
            </div>
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Departments
              </dt>
              <dd className="text-[13px] font-medium">
                {user.departments.join(', ') || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Tier
              </dt>
              <dd className="text-[13px] font-medium capitalize">{user.role}</dd>
            </div>
          </dl>

          <div className="flex flex-wrap items-center gap-2 mt-5">
            <Button onClick={() => router.push('/chat')}>Open chat</Button>
            {isAdmin && (
              <Button variant="secondary" onClick={() => router.push('/admin/audit')}>
                View audit log
              </Button>
            )}
            <Button
              variant="outline"
              onClick={onLogout}
              className="hover:text-destructive hover:border-destructive/40"
            >
              Sign out
            </Button>
          </div>
        </div>

        {/* Lower grid */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1.15fr] gap-4">
          <RecentQueries />
          <DemoQuestions departments={user.departments} />
        </div>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/me/page.tsx
git commit -m "feat(frontend): /me identity hero + dashboard composition

- Identity card: 56px gradient avatar (inline oklch style so the tile
  doesn't require a new token), title + tenant subtitle, tenant-acronym
  logo placeholder tile (hidden on <sm), 3-col meta grid (Max clearance /
  Departments / Tier).
- Actions row re-adds 'Open chat' + role-gated 'View audit log' + 'Sign
  out' (per Pass 2 spec §2B — page CTAs, not nav; TopNav owns nav).
- Lower 1fr 1.15fr grid: RecentQueries | DemoQuestions. Mobile stacks."
```

---

## Task 13: `/login` — DemoAccountPicker component

**Files:**
- Create: `frontend/app/login/components/DemoAccountPicker.tsx`

**Goal:** A 4-col responsive grid of 8 demo-account cards + 1 dashed "Custom login" tile. Click fills the parent form's tenant/username/password fields via callback. Selected card shows `border-primary + ring-3 ring-accent + CheckCircle2` icon.

- [ ] **Step 1: Create `DemoAccountPicker.tsx`.**

```tsx
"use client";

import { CheckCircle2, Pencil } from "lucide-react";

interface DemoAccount {
  username: string;
  tier: "Employee" | "Manager" | "Director" | "Executive";
  note: string;
}

const ACCOUNTS: readonly DemoAccount[] = [
  { username: "employee.security", tier: "Employee", note: "Sees least; great for refusal shots" },
  { username: "manager.hr", tier: "Manager", note: "Sees restricted HR docs" },
  { username: "manager.engineering", tier: "Manager", note: "Gets refusals on HR queries" },
  { username: "director.engineering", tier: "Director", note: "Sees most engineering docs" },
  { username: "director.security", tier: "Director", note: "Sees secret security docs" },
  { username: "executive.fleet", tier: "Executive", note: "Wide clearance, narrow dept" },
  { username: "executive.procurement", tier: "Executive", note: "Sees HR + procurement" },
  { username: "employee.engineering", tier: "Employee", note: "Refusals on HR + Security" },
];

export function DemoAccountPicker({
  selected,
  onPick,
  onCustom,
}: {
  /** Username of the currently-selected demo card, or null for custom. */
  selected: string | null;
  onPick: (username: string, password: string) => void;
  onCustom: () => void;
}) {
  return (
    <div className="p-6 sm:p-8 bg-muted border-t border-border rounded-b-lg">
      <div className="text-[10px] font-mono uppercase tracking-[0.1em] text-subtle mb-3">
        Demo accounts · all password imperial-march
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {ACCOUNTS.map((a) => {
          const active = a.username === selected;
          return (
            <button
              key={a.username}
              type="button"
              onClick={() => onPick(a.username, "imperial-march")}
              className={`relative text-left p-3 rounded-md bg-card border transition ${
                active
                  ? "border-primary ring-[3px] ring-accent"
                  : "border-border hover:border-border-strong hover:-translate-y-0.5"
              }`}
            >
              {active && (
                <CheckCircle2
                  className="absolute top-2 right-2 w-4 h-4 text-primary"
                  aria-hidden
                />
              )}
              <div className="font-mono text-[12px] font-semibold truncate">
                {a.username}
              </div>
              <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-subtle mt-0.5">
                {a.tier}
              </div>
              <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                {a.note}
              </div>
            </button>
          );
        })}
        <button
          type="button"
          onClick={onCustom}
          className={`relative text-left p-3 rounded-md border-2 border-dashed transition flex items-center gap-2 ${
            selected === null
              ? "border-primary text-primary"
              : "border-border text-muted-foreground hover:border-border-strong hover:text-foreground"
          }`}
        >
          <Pencil className="w-4 h-4 shrink-0" aria-hidden />
          <div>
            <div className="font-mono text-[12px] font-semibold">Custom login</div>
            <div className="text-[11px] mt-0.5">Type your own credentials</div>
          </div>
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/login/components/DemoAccountPicker.tsx
git commit -m "feat(frontend): /login DemoAccountPicker component

4-col responsive grid of 8 known demo accounts + 1 dashed 'Custom login'
tile. Selected card = border-primary + ring-3 ring-accent + CheckCircle2.
Click callbacks: onPick(username, password) fills the form; onCustom()
clears + focuses the form. Rendered inside a bg-muted footer with a
'Demo accounts · all password imperial-march' mono heading."
```

---

## Task 14: `/login` — 2-col branded split + form panel + integrate picker

**Files:**
- Modify: `frontend/app/login/page.tsx`

**Goal:** Rewrite `/login` as a centered card containing a 2-col grid (`1fr 1fr`, `min-h-[560px]`). Left = branded indigo gradient panel with HOLOCRON mark + headline + 2 feature pills. Right = form panel with 3 icon-prefixed fields at 40px + submit. Below the grid: `DemoAccountPicker`. Mobile: single column, brand panel above form.

- [ ] **Step 1: Overwrite `login/page.tsx`.**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import {
  ArrowRight,
  Building2,
  Database,
  Eye,
  EyeOff,
  FileText,
  GitCompareArrows,
  KeyRound,
  User as UserIcon,
} from 'lucide-react';

import { api } from '@/lib/api';

import { DemoAccountPicker } from './components/DemoAccountPicker';

function fieldClasses(): string {
  return (
    'w-full h-10 pl-9 pr-3 rounded-md bg-card border border-border-strong text-sm ' +
    'focus:outline-none focus:border-primary focus:ring-[3px] focus:ring-accent transition'
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [tenantId, setTenantId] = useState(process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedDemo, setSelectedDemo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const usernameRef = useRef<HTMLInputElement | null>(null);

  function pickDemo(u: string, p: string) {
    setUsername(u);
    setPassword(p);
    setSelectedDemo(u);
    setError(null);
  }

  function chooseCustom() {
    setUsername('');
    setPassword('');
    setSelectedDemo(null);
    setError(null);
    usernameRef.current?.focus();
  }

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
    <main className="min-h-screen bg-muted flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-5xl bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 min-h-[560px]">
          {/* Left: branded panel */}
          <div
            className="relative p-10 text-primary-foreground flex flex-col justify-between"
            style={{
              background:
                'linear-gradient(155deg, oklch(0.28 0.05 264) 0%, oklch(0.22 0.03 257) 100%)',
            }}
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.14]"
              style={{
                backgroundImage:
                  'radial-gradient(circle at center, oklch(0.985 0.004 247) 1px, transparent 1.5px)',
                backgroundSize: '22px 22px',
              }}
              aria-hidden
            />
            <div className="relative">
              <div className="flex items-center gap-2 font-mono text-[13px] font-semibold tracking-[0.18em]">
                <div className="w-8 h-8 rounded-md bg-primary/60 grid place-items-center">
                  <Database className="w-4 h-4" aria-hidden />
                </div>
                HOLOCRON
              </div>
              <h1 className="mt-8 text-[26px] font-semibold leading-tight tracking-[-0.015em] max-w-md">
                Imperial Knowledge Assistant
              </h1>
              <p className="mt-3 text-[14px] leading-relaxed max-w-md text-primary-foreground/85">
                Ask a question. Cite it. See conflicts. Refuse when you must.
                One clearance-aware assistant across every department.
              </p>
            </div>
            <div className="relative flex flex-wrap gap-2 mt-6">
              <FeaturePill icon={<FileText className="w-3.5 h-3.5" aria-hidden />} label="Cited sources" />
              <FeaturePill icon={<GitCompareArrows className="w-3.5 h-3.5" aria-hidden />} label="Conflict detection" />
            </div>
          </div>

          {/* Right: form panel */}
          <div className="p-8 sm:p-10 bg-card">
            <h2 className="text-[18px] font-semibold mb-6">Sign in</h2>
            <form className="space-y-4" onSubmit={onSubmit}>
              <FieldWrapper label="Tenant ID" htmlFor="tenant">
                <Building2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  id="tenant"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  placeholder="Tenant UUID"
                  required
                  className={`${fieldClasses()} font-mono text-[12px]`}
                />
              </FieldWrapper>
              <FieldWrapper label="Username" htmlFor="username">
                <UserIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  ref={usernameRef}
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. executive.fleet"
                  required
                  className={fieldClasses()}
                />
              </FieldWrapper>
              <FieldWrapper label="Password" htmlFor="password">
                <KeyRound className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className={`${fieldClasses()} pr-9`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </FieldWrapper>
              {error && <p className="text-[12px] text-destructive">{error}</p>}
              <button
                type="submit"
                disabled={submitting}
                className="w-full h-10 rounded-md bg-foreground text-background text-[13px] font-medium flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-60 transition"
              >
                {submitting ? 'Signing in…' : (
                  <>
                    Sign in <ArrowRight className="w-4 h-4" aria-hidden />
                  </>
                )}
              </button>
              <div className="flex items-center justify-between text-[11px] font-mono text-subtle mt-2">
                <span>demo password: imperial-march</span>
              </div>
            </form>
          </div>
        </div>

        {/* Demo picker footer */}
        <DemoAccountPicker
          selected={selectedDemo}
          onPick={pickDemo}
          onCustom={chooseCustom}
        />
      </div>
    </main>
  );
}

function FeaturePill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-primary/40 text-primary-foreground text-[12px] font-mono uppercase tracking-[0.08em]">
      {icon}
      {label}
    </div>
  );
}

function FieldWrapper({
  htmlFor,
  label,
  children,
}: {
  htmlFor: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={htmlFor}
        className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground"
      >
        {label}
      </label>
      <div className="relative">{children}</div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/login/page.tsx
git commit -m "feat(frontend): /login 2-col branded split + demo picker integration

- Centered card wrapper (max-w-5xl) with 2-col grid inside:
  - Left: indigo gradient panel with dot-grid overlay, HOLOCRON mark
    (Database icon in translucent tile), 'Imperial Knowledge Assistant'
    headline, value copy, 2 feature pills (Cited sources, Conflict detection).
  - Right: form panel with icon-prefixed fields at 40px, focused-state
    ring (border-primary + ring-3 ring-accent per handoff), password
    show/hide toggle, dark full-width Submit with ArrowRight.
- Footer: DemoAccountPicker (Task 13) with picked/custom-login state
  management inside the login page.
- Mobile: grid collapses to 1 col (brand panel above form); picker grid
  → 2 → 1 cols."
```

---

## Task 15: `/admin/audit` — SummaryStats component

**Files:**
- Create: `frontend/app/admin/audit/components/SummaryStats.tsx`

**Goal:** 3-card row: Queries today (Activity icon, accent tile), Refusals today (Lock icon, restricted tile), Conflicts today (GitCompareArrows icon, conflict tile). Fetches via `api.auditSummary()`.

- [ ] **Step 1: Create `SummaryStats.tsx`.**

```tsx
"use client";

import { useEffect, useState } from "react";
import { Activity, GitCompareArrows, Lock, type LucideIcon } from "lucide-react";

import { api } from "@/lib/api";
import type { AuditSummary } from "@/lib/types/audit-summary";

interface StatDef {
  key: keyof AuditSummary;
  label: string;
  icon: LucideIcon;
  tileClass: string;
}

const STATS: StatDef[] = [
  {
    key: "queries_today",
    label: "Queries today",
    icon: Activity,
    tileClass: "bg-accent text-accent-foreground",
  },
  {
    key: "refusals_today",
    label: "Refusals today",
    icon: Lock,
    tileClass: "bg-restricted text-restricted-foreground",
  },
  {
    key: "conflicts_today",
    label: "Conflicts today",
    icon: GitCompareArrows,
    tileClass: "bg-conflict text-conflict-foreground",
  },
];

export function SummaryStats() {
  const [data, setData] = useState<AuditSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .auditSummary()
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {STATS.map((s) => {
        const Icon = s.icon;
        const value = data ? data[s.key] : null;
        return (
          <div
            key={s.key}
            className="bg-card border border-border rounded-lg p-4 flex items-center gap-3"
          >
            <div className={`w-10 h-10 rounded-md grid place-items-center shrink-0 ${s.tileClass}`}>
              <Icon className="w-5 h-5" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle">
                {s.label}
              </div>
              <div className="text-[22px] font-semibold leading-tight tabular-nums">
                {value === null ? (error ? "—" : "…") : value.toLocaleString()}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/app/admin/audit/components/SummaryStats.tsx
git commit -m "feat(frontend): /admin/audit SummaryStats component

3-card row: Queries today (Activity, accent tile), Refusals today (Lock,
restricted tile), Conflicts today (GitCompareArrows, conflict tile).
Fetches once on mount from /admin/audit/summary (Task 2 endpoint). Shows
'…' during load, '—' on error."
```

---

## Task 16: `/admin/audit` — DataTable primitive + AuditRow rewrite

**Files:**
- Create: `frontend/app/admin/audit/components/DataTable.tsx`
- Modify: `frontend/app/admin/audit/components/AuditRow.tsx`

**Goal:** A CSS-grid-based `DataTable` primitive that replaces the `<table>` markup. Grid columns `150px 1.4fr 90px 90px 90px 40px`. Mono uppercase header row on `bg-muted`. Zebra rows via `even:bg-[oklch(0.988_0.003_247)]`. Row hover `bg-muted`. Expand chevron rotates on click. AuditRow gets an initials avatar cell.

- [ ] **Step 1: Create `DataTable.tsx`.**

```tsx
"use client";

import type { ReactNode } from "react";

export const AUDIT_COLUMNS = "150px 1.4fr 90px 90px 90px 40px";

const HEADERS: ReadonlyArray<{ label: string; align?: "left" | "right" }> = [
  { label: "Time (UTC)" },
  { label: "User" },
  { label: "Latency", align: "right" },
  { label: "Refusal" },
  { label: "Conflict" },
  { label: "", align: "right" },
];

export function DataTable({
  isEmpty,
  emptyState,
  children,
}: {
  isEmpty: boolean;
  emptyState: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div className="overflow-x-auto">
        <div className="min-w-[760px]">
          {/* Sticky header */}
          <div
            className="grid bg-muted border-b border-border sticky top-0 z-10"
            style={{ gridTemplateColumns: AUDIT_COLUMNS }}
          >
            {HEADERS.map((h, i) => (
              <div
                key={i}
                className={`px-3 py-2 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground ${
                  h.align === "right" ? "text-right" : "text-left"
                }`}
              >
                {h.label}
              </div>
            ))}
          </div>
          {/* Body */}
          <div>
            {isEmpty ? emptyState : children}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `AuditRow.tsx`.**

Replace the contents entirely — it now emits CSS-grid rows, not `<tr>`:

```tsx
"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import type { AuditRow as AuditRowType } from "@/lib/types/audit";
import { initials } from "@/lib/initials";

import { AuditEventDetail } from "./AuditEventDetail";
import { AUDIT_COLUMNS } from "./DataTable";

export function AuditRow({ row, index }: { row: AuditRowType; index: number }) {
  const [open, setOpen] = useState(false);
  const zebra = index % 2 === 1 ? "bg-[oklch(0.988_0.003_247)]" : "";
  const activeTint = open ? "bg-accent" : "";
  const shortUser = row.user_id?.slice(0, 8) ?? "—";
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full grid text-left ${zebra} ${activeTint} hover:bg-muted transition`}
        style={{ gridTemplateColumns: AUDIT_COLUMNS }}
        aria-expanded={open}
      >
        <div className="px-3 py-2 font-mono text-[12px] text-foreground">
          {row.first_event_at.slice(0, 19).replace("T", " ")}
        </div>
        <div className="px-3 py-2 flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-full bg-accent text-accent-foreground grid place-items-center font-mono text-[10px] font-semibold shrink-0">
            {initials(shortUser)}
          </div>
          <span className="font-mono text-[12px] truncate">{shortUser}</span>
        </div>
        <div className="px-3 py-2 text-right font-mono text-[12px] text-muted-foreground">
          {row.latency_ms} ms
        </div>
        <div className="px-3 py-2">
          {row.had_refusal ? (
            <span className="px-2 py-0.5 rounded-sm bg-restricted text-restricted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              yes
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-sm bg-muted text-muted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              no
            </span>
          )}
        </div>
        <div className="px-3 py-2">
          {row.had_conflict ? (
            <span className="px-2 py-0.5 rounded-sm bg-conflict text-conflict-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              yes
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-sm bg-muted text-muted-foreground font-mono text-[10px] uppercase tracking-[0.08em]">
              no
            </span>
          )}
        </div>
        <div className="px-3 py-2 flex items-center justify-end">
          <ChevronRight
            className={`w-4 h-4 text-muted-foreground transition-transform ${
              open ? "rotate-90" : ""
            }`}
            aria-hidden
          />
        </div>
      </button>
      {open && (
        <div className="bg-muted px-4 py-3 border-t border-border space-y-2">
          {row.events.map((e, i) => (
            <AuditEventDetail key={i} event={e} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS. (`AuditRow` is now index-aware; the page.tsx composition in Task 17 will pass `index`.)

- [ ] **Step 4: Commit.**

```
git add frontend/app/admin/audit/components/DataTable.tsx frontend/app/admin/audit/components/AuditRow.tsx
git commit -m "feat(frontend): /admin/audit DataTable primitive + AuditRow rewrite

- DataTable.tsx: CSS-grid table with sticky header. Columns exported as
  AUDIT_COLUMNS constant so AuditRow can grid-match.
- AuditRow: <button> row instead of <tr> (semantic accordion),
  initials avatar in User cell, YES/NO pills use bg-restricted/bg-conflict
  vs bg-muted, ChevronRight rotates 90° on open. Zebra via
  index-parity + oklch shade. Active-open row tinted bg-accent.
- Detail area moves out from a nested <tr> into an inline div under the
  row button — cleaner grid semantics."
```

---

## Task 17: `/admin/audit` — chip filter bar + page composition

**Files:**
- Modify: `frontend/app/admin/audit/components/AuditFilters.tsx`
- Modify: `frontend/app/admin/audit/page.tsx`

**Goal:** Replace the form-shaped filters with a chip / segmented-control bar (Refusals `All | Refusals`, Conflicts `All | Conflicts`, date-range chip, right-aligned Clear link). Rewire `/admin/audit/page.tsx` to render SummaryStats + new filter bar + DataTable (with `AuditRow` index-aware) + Load more (shadcn Button with ChevronDown) + updated empty state.

- [ ] **Step 1: Rewrite `AuditFilters.tsx`.**

```tsx
"use client";

import { Calendar, X } from "lucide-react";

import type { AuditQuery } from "@/lib/types/audit";

function segClasses(active: boolean, activeClass: string): string {
  const base =
    "px-3 py-1 text-[12px] font-mono uppercase tracking-[0.08em] transition first:rounded-l-sm last:rounded-r-sm";
  return active ? `${base} ${activeClass}` : `${base} bg-muted text-muted-foreground hover:text-foreground`;
}

export function AuditFilters({
  value,
  onChange,
}: {
  value: AuditQuery;
  onChange: (q: AuditQuery) => void;
}) {
  const refusalAll = value.has_refusal !== true;
  const refusalOn = value.has_refusal === true;
  const conflictAll = value.has_conflict !== true;
  const conflictOn = value.has_conflict === true;
  const hasDateRange = Boolean(value.start || value.end);
  const hasAnyFilter = refusalOn || conflictOn || hasDateRange;

  return (
    <div className="flex flex-wrap items-center gap-3 py-2">
      {/* Refusals segmented */}
      <div className="inline-flex rounded-sm border border-border overflow-hidden">
        <button
          type="button"
          onClick={() => onChange({ ...value, has_refusal: undefined })}
          className={segClasses(refusalAll, "bg-card text-foreground")}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onChange({ ...value, has_refusal: true })}
          className={segClasses(refusalOn, "bg-restricted text-restricted-foreground")}
        >
          Refusals
        </button>
      </div>

      {/* Conflicts segmented */}
      <div className="inline-flex rounded-sm border border-border overflow-hidden">
        <button
          type="button"
          onClick={() => onChange({ ...value, has_conflict: undefined })}
          className={segClasses(conflictAll, "bg-card text-foreground")}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onChange({ ...value, has_conflict: true })}
          className={segClasses(conflictOn, "bg-conflict text-conflict-foreground")}
        >
          Conflicts
        </button>
      </div>

      {/* Date range chip — inline datetime-local inputs, hidden until you focus,
          simpler than a full popover for demo. */}
      <div className="inline-flex items-center gap-2 rounded-sm border border-border px-2.5 py-1 bg-card">
        <Calendar className="w-3.5 h-3.5 text-muted-foreground" aria-hidden />
        <input
          type="datetime-local"
          value={value.start ?? ""}
          onChange={(e) => onChange({ ...value, start: e.target.value || undefined })}
          className="bg-transparent text-[12px] font-mono text-foreground outline-none"
          aria-label="Start"
        />
        <span className="text-subtle text-[12px]">→</span>
        <input
          type="datetime-local"
          value={value.end ?? ""}
          onChange={(e) => onChange({ ...value, end: e.target.value || undefined })}
          className="bg-transparent text-[12px] font-mono text-foreground outline-none"
          aria-label="End"
        />
      </div>

      {hasAnyFilter && (
        <button
          type="button"
          onClick={() => onChange({})}
          className="ml-auto inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground"
        >
          <X className="w-3 h-3" aria-hidden />
          Clear
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `admin/audit/page.tsx`.**

```tsx
"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ScrollText } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchAuditPage } from "@/lib/audit-api";
import type {
  AuditPage,
  AuditQuery,
  AuditRow as AuditRowType,
} from "@/lib/types/audit";

import { AuditFilters } from "./components/AuditFilters";
import { AuditRow } from "./components/AuditRow";
import { DataTable } from "./components/DataTable";
import { SummaryStats } from "./components/SummaryStats";

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
      setRows((prev) => (reset ? page.rows : [...prev, ...page.rows]));
      setCursor(page.next_cursor);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const emptyStateNode = (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center">
      <ScrollText className="w-6 h-6 text-muted-foreground" aria-hidden />
      <div className="text-[13px] text-muted-foreground">
        No audit rows for the current filter.
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold">Audit log</h1>
        <p className="text-[13px] text-muted-foreground mt-1">
          One row per <code className="font-mono text-[12px]">correlation_id</code> (one
          /chat/ask = one row). Click any row to inspect the underlying query,
          retrieved IDs, refusal ref, response, and conflict subjects.{" "}
          <span className="text-subtle">Director / Executive only.</span>
        </p>
      </div>

      <SummaryStats />

      <AuditFilters value={filters} onChange={setFilters} />

      {error && (
        <div className="border border-destructive/40 bg-destructive/10 text-destructive rounded-md p-3 text-sm">
          {error}
        </div>
      )}

      <DataTable isEmpty={rows.length === 0 && !loading} emptyState={emptyStateNode}>
        {rows.map((r, i) => (
          <AuditRow key={r.correlation_id} row={r} index={i} />
        ))}
      </DataTable>

      {cursor && (
        <Button variant="outline" disabled={loading} onClick={() => load(false)}>
          <ChevronDown className="w-4 h-4 mr-1" aria-hidden />
          {loading ? "Loading…" : "Load more"}
        </Button>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build.**

From `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 4: Commit.**

```
git add frontend/app/admin/audit/components/AuditFilters.tsx frontend/app/admin/audit/page.tsx
git commit -m "feat(frontend): /admin/audit chip filter bar + page composition

- AuditFilters rewritten as a chip / segmented-control bar: Refusals
  All|Refusals, Conflicts All|Conflicts, date-range chip with Calendar
  icon + inline datetime-local inputs. 'Clear' link right-aligned, only
  visible when any filter is set.
- Page composition: Header + SummaryStats row + AuditFilters + DataTable
  (using AuditRow index-aware zebra) + Load more as shadcn Button with
  ChevronDown. Empty state = centered ScrollText icon + copy."
```

---

## Task 18: Final gates + CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md`

**Goal:** Run the final quality gates, update CLAUDE.md so Phase E is marked ✅ (both passes done).

- [ ] **Step 1: Final backend test gate.**

From `backend/` with venv activated:
```
python -m pytest -q
```
Expected: `187 passed` (181 baseline + 3 Task 1 tests + 3 Task 2 tests).

- [ ] **Step 2: Final frontend build gate.**

From `frontend/`: `pnpm build`
Expected: build succeeds. Note the Route table for the CLAUDE.md write-up.

- [ ] **Step 3: Final token-hygiene sweep.**

From `frontend/`:
```
grep -rE "\b(slate|gray)-[0-9]+" app components || echo NONE
```
Expected: `NONE`.

```
grep -rE "🔒|⚠" app components || echo NONE
```
Expected: `NONE`.

- [ ] **Step 4: Manual walkthrough.**

Start dev servers:
- Backend terminal: `cd backend && .\.venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8000`
- Frontend terminal: `cd frontend && pnpm dev`

Walk:
1. `/login` — see the branded split, click a demo account, see fields fill + active card highlight, click Sign in.
2. `/me` — identity hero card with gradient avatar, meta grid, "Open chat" / "View audit log" (if director/exec) / "Sign out" buttons. Recent queries + demo questions grid.
3. Click "Try a demo question" card → land on `/chat` with the question prefilled and sent. Assistant response should show the `Sparkles + Holocron + N sources · N conflicts · N.NNs` header, redesigned CitationCards with hover lift, and (if applicable) a ConflictCard split-diff.
4. Sign in as `employee.security` and ask "What's the dress-code policy for off-base events?" → RefusalNote hero renders with accent Lock circle + "Request access" button. Click it → button flashes "Copied ✓".
5. Sign in as `executive.procurement` → visit `/admin/audit`. See 3-card SummaryStats row, chip filter bar, DataTable with initials avatars. Toggle "Refusals" chip → rows filter. Expand a row → detail area shows correctly.
6. Resize to 375px viewport — every route stays usable, ConflictCard stacks vertically with horizontal VS divider.

Stop dev servers.

- [ ] **Step 5: Update CLAUDE.md — flip Phase E to ✅.**

Open `CLAUDE.md`. Find the Phase E section that starts `- **Phase E — Frontend Revamp:** 🟡`. Replace that entire bullet with:

```markdown
- **Phase E — Frontend Revamp:** ✅ **CODE COMPLETE (Pass 1 + Pass 2).** Pass 1 (Foundation) merged to `main` on 2026-07-01: design tokens seeded from the local (gitignored) [design handoff](handoffs/design_handoff_holocron_frontend/README.md); every `slate-*`/`gray-*` migrated to semantic tokens; `.dark` block deleted; two emoji swapped for lucide icons; `TopNav` primitive persistent on `/me`, `/chat`, `/admin/*`; `ClearanceBadge` + `CitationChip` polished; mobile breakpoints on all 4 routes. Pass 2 (Hero) merged to `main` on 2026-07-01: two additive read-only backend endpoints (`GET /me/recent-queries` + `GET /admin/audit/summary`, ~6 new tests, total 187 backend tests); `/login` 2-col branded split + `DemoAccountPicker`; `/me` identity hero + `RecentQueries` + `DemoQuestions` dashboard; `/chat` `CitationCard` hero (hover lift), `ConflictCard` split-diff with VS spine, `RefusalNote` hero with "Request access" copy-ref-to-clipboard, `EmptyState` hero with dept-seeded demo cards, `MessageAssistant` "Holocron" header with client-measured latency, `?q=…` prefill hook; `/admin/audit` `SummaryStats` row + chip/segmented filter bar + `DataTable` primitive with sticky header + zebra + initials avatar cell. Frontend has no test framework — verification is `pnpm build` + manual browser walk. See [spec](docs/superpowers/specs/2026-07-01-phase-e-frontend-revamp-design.md) · [Pass 1 plan](docs/superpowers/plans/2026-07-01-phase-e-pass-1-foundation.md) · [Pass 2 plan](docs/superpowers/plans/2026-07-01-phase-e-pass-2-hero.md).
```

- [ ] **Step 6: Commit.**

```
git add CLAUDE.md
git commit -m "docs(claude.md): mark Phase E complete (Pass 1 + Pass 2 done)

Phase E flipped from 🟡 to ✅. Backend now at 187 tests (2 additive
read-only endpoints for /me/recent-queries + /admin/audit/summary).
Frontend hero pass adds /login demo picker, /me dashboard, /chat hero
components, /admin/audit summary + data-table."
```

- [ ] **Step 7: Merge decision point.**

You are on `phase-e-pass-2` with all Pass 2 commits. Same three options as Pass 1's Task 12 Step 9:

**A. Merge to main:**
```
git checkout main
git merge --ff-only phase-e-pass-2
git branch -d phase-e-pass-2
```
Then push if desired: `git push origin main`.

**B. Keep the branch** for follow-up polish.

**C. Open a PR** for review: `git push -u origin phase-e-pass-2 && gh pr create ...`

If solo-driving and confident, A is the clean landing.

---

## Summary of shipped artifacts (Pass 2)

**Backend created:**
- `backend/app/api/user.py`
- `backend/tests/test_recent_queries_endpoint.py`

**Backend modified:**
- `backend/app/repositories/audit_repository.py` (adds `list_recent_queries` + `summary_counts`)
- `backend/app/api/admin.py` (adds `/admin/audit/summary`)
- `backend/app/main.py` (registers `user_router`)
- `backend/tests/test_admin_audit_endpoint.py` (adds 3 summary tests)

**Frontend created:**
- `frontend/lib/initials.ts`
- `frontend/lib/demo-questions.ts`
- `frontend/lib/types/user.ts`
- `frontend/lib/types/audit-summary.ts`
- `frontend/app/chat/components/EmptyState.tsx`
- `frontend/app/me/components/RecentQueries.tsx`
- `frontend/app/me/components/DemoQuestions.tsx`
- `frontend/app/login/components/DemoAccountPicker.tsx`
- `frontend/app/admin/audit/components/SummaryStats.tsx`
- `frontend/app/admin/audit/components/DataTable.tsx`

**Frontend modified:**
- `frontend/lib/api.ts` (adds `recentQueries` + `auditSummary`)
- `frontend/components/TopNav.tsx` (uses shared `initials`)
- `frontend/app/chat/components/CitationCard.tsx` (hero rewrite)
- `frontend/app/chat/components/ConflictCard.tsx` (split-diff hero)
- `frontend/app/chat/components/RefusalNote.tsx` (hero + copy-ref)
- `frontend/app/chat/components/MessageAssistant.tsx` (header row + latency prop)
- `frontend/app/chat/components/ChatThread.tsx` (Turn.assistant carries `latencyMs`)
- `frontend/app/chat/page.tsx` (latency measurement + prefill + EmptyState)
- `frontend/app/me/page.tsx` (dashboard composition)
- `frontend/app/login/page.tsx` (branded split + picker)
- `frontend/app/admin/audit/components/AuditRow.tsx` (grid row + avatar + chevron)
- `frontend/app/admin/audit/components/AuditFilters.tsx` (chip/segmented rebuild)
- `frontend/app/admin/audit/page.tsx` (composition with SummaryStats + DataTable)
- `CLAUDE.md` (Phase E ✅)

**Not shipped in Pass 2** (deferred to Phase F):
- Contradicting-phrase `<mark>` highlighting in ConflictCard (needs LLM structured output)
- Dark mode toggle (out of scope — the tokens exist but dark hero mocks don't)
- Streaming `/chat/ask` (SSE)
- Real-Groq slow test
- Additional per-tenant customization of demo-question map
