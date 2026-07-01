---
name: HOLOCRON Phase E — Frontend Revamp
status: Locked (brainstorm)
date: 2026-07-01
owner: Lutfi
phase: E
target_window: ~10–14 hrs (Pass 1: 4–6 hrs · Pass 2: 6–8 hrs)
predecessors:
  - docs/superpowers/specs/2026-06-27-holocron-design.md
  - docs/superpowers/specs/2026-06-28-phase-d-eval-audit-polish.md
  - docs/superpowers/plans/2026-06-28-phase-d-eval-audit-polish-completion.md
design_reference:
  - handoffs/design_handoff_holocron_frontend/README.md
  - handoffs/design_handoff_holocron_frontend/Holocron Visual Target.dc.html
---

# HOLOCRON Phase E — Frontend Revamp

## 1. Goal

Phase E takes the working post-MVP frontend (functional but visually inconsistent, hand-coded `slate-*`/`gray-*`, mixed radii, emoji icons) and lands it on the design system already delivered in [handoffs/design_handoff_holocron_frontend/](../../../handoffs/design_handoff_holocron_frontend/). End state is a **portfolio-screenshot-quality** frontend across every user-facing route — the visual pass that turns the two flagship demos (clearance-filtered retrieval + conflict detection) into the money-shots a recruiter opens the repo for.

Phase E does NOT add new product capabilities. It ships a token migration, two shared primitives, a persistent top nav, per-route hero redesigns, and mobile breakpoints. Two small additive backend endpoints are in-scope because two dashboard components need data the backend doesn't currently expose.

Phase E is **not part of the MVP**. It ships in two independent merges (Pass 1 = foundation refactor · Pass 2 = hero components), each demoable on its own. The "Deferred to Phase E / post-MVP" bucket in CLAUDE.md is renamed to **Phase F**.

## 2. In-scope deliverables

Two passes, each ends at a demoable milestone.

### Pass 1 — Foundation (mechanical refactor, safe, no new components)

Ordered by dependency:

1. **Seed tokens in `frontend/app/globals.css`.**
   - Add oklch values from the handoff's Token panel to `:root`: `--background`, `--surface` (new), `--card`, `--muted`, `--foreground`, `--muted-foreground`, `--subtle` (new), `--border`, `--border-strong` (new), `--primary`, `--primary-fg`, `--accent`, `--accent-fg`.
   - Add semantic clearance/state groups as CSS vars: `--public-{bg,fg,border}`, `--restricted-*`, `--secret-*`, `--top-secret-*`, `--conflict-{bg,fg,border}`.
   - Add radius scale: `--r-sm: 8px`, `--r-md: 10px`, `--r-lg: 14px`.
   - **Delete the entire `.dark` block.** No dark mode in Phase E.
   - Keep the Phase D shadcn/Tailwind bridge intact — it is load-bearing.

2. **Update `frontend/tailwind.config.ts`.**
   - Extend `theme.borderRadius` with `sm/md/lg` mapped to `var(--r-sm/md/lg)`.
   - Extend `theme.colors` to expose `surface`, `border-strong`, `subtle`, and the clearance/state groups (`public`, `public-foreground`, `public-border`, and the same for restricted, secret, top-secret, conflict).
   - Extend `theme.fontFamily.mono` to reference `var(--font-geist-mono)` so mono metadata utilities are cheap.

3. **Migrate emoji → lucide-react icons.**
   - 🔒 in `RefusalNote` → `<Lock />`.
   - ⚠ in `MessageAssistant` conflicts section → `<TriangleAlert />`.
   - Small, isolated; unblocks visual audits.

4. **Migrate `slate-*` / `gray-*` → semantic tokens across all 4 routes.**
   - Chat: `slate-800` bubble → `bg-foreground text-background`; `slate-50` bubble → `bg-card`; scattered `slate-500` metadata → `text-muted-foreground`.
   - Audit: `gray-*` → `bg-card` / `bg-muted` / `text-muted-foreground` as appropriate.
   - Radius sweep at the same time: chat bubbles `rounded-2xl` → `rounded-lg`, table `rounded` → `rounded-lg`, keep inputs at `rounded-md`.
   - Verify by opening every route: app should look **the same or slightly more unified**, not visually different. This is a refactor, not a redesign.

5. **Ship the `TopNav` primitive.**
   - New file: `frontend/components/TopNav.tsx`.
   - 62px, `bg-card`, bottom hairline. Left: HOLOCRON mono wordmark + tab links (Home / Chat / Audit log) with a 2px `--primary` underline on the active tab. Use `usePathname` from `next/navigation` for active-state detection.
   - Right: `ClearanceBadge` + initials avatar (accent circle).
   - "Audit log" tab role-gated (`director` or `executive` only) — read from the same client-side session hook as `/me`.
   - Insert into `/me`, `/chat`, `/admin/audit` layouts. NOT `/login`.
   - Once TopNav ships, the two Phase D nav-fix commits (`ace4485`, `8e14594`) become partially obsolete — remove the ad-hoc `/me` "Open chat" / "View audit log" buttons that were prevention-only, and remove the inline top-of-`/chat` header bar.

6. **Polish `ClearanceBadge` and citation chip primitives.**
   - `ClearanceBadge` ([frontend/components/ClearanceBadge.tsx](../../../frontend/components/ClearanceBadge.tsx) + [lib/clearance-color.ts](../../../frontend/lib/clearance-color.ts)): migrate hard-coded `green-100`/`amber-100`/`red-100` to `bg-public`/`bg-restricted`/`bg-secret`/`bg-top-secret` semantic tokens. Tighten to mono 11px/600 with `0.07em` tracking; dot + label pattern per handoff.
   - **Citation chip:** new primitive at `frontend/components/CitationChip.tsx`. States: default = `bg-accent text-accent-foreground`, hover = `bg-primary text-primary-foreground`, active = `bg-primary` + `ring-3 ring-accent`. `rounded-sm` (5px), mono 12px/600, `min-w-[20px]`. Used inline in answer text; anchors to `#cite-{n}`.

7. **Mobile breakpoints on all 4 routes.**
   - `/login`: form stays center; Pass 2's split layout collapses to single column below `md`.
   - `/me`: current single card is fine; Pass 2 dashboard grid will stack.
   - `/chat`: citation grid already drops to 1 col; ensure `TopNav` doesn't wrap and thread spacing works down to 375px.
   - `/admin/audit`: wrap `<table>` in horizontal-scroll container with `min-w-[720px]` — temporary shim; Pass 2 replaces the table entirely.

**Pass 1 verification.** `pnpm build` clean · every route renders (no visual regression, just unification) · zero `slate-*`/`gray-*` grep hits in `frontend/app/**/*.tsx` and `frontend/components/**/*.tsx` · `.dark` block removed from `globals.css` · `TopNav` renders on `/me`, `/chat`, `/admin/audit` with correct active state and role gating · mobile viewport (375px) doesn't break any route.

### Pass 2 — Hero components (net-new visual work, screenshot money-shots)

Exact visual specs (oklch values, spacing, focused-field ring, gradient panels, dot-grid overlays, etc.) live in [handoffs/design_handoff_holocron_frontend/README.md](../../../handoffs/design_handoff_holocron_frontend/README.md) and `Holocron Visual Target.dc.html`. This spec captures scope and behavior, not markup.

**2A. `/login` — branded 2-col split + demo picker.**

- New layout: centered card frame containing a 2-col grid (`1fr 1fr`, `min-h-[560px]`). Left = branded indigo panel (gradient bg + dot-grid overlay + HOLOCRON mark + headline + value copy + 2 feature pills). Right = form panel with H3 + 3 fields (Tenant/Username/Password) at 40px height + full-width dark submit.
- Icons: `Building2` on Tenant, `User` on Username, `KeyRound` + `Eye` on Password, `ArrowRight` on Submit.
- Field focused state per handoff: 1.5px `border-primary` + `ring-3 ring-accent`.
- **New: DemoAccountPicker** (`frontend/app/login/components/DemoAccountPicker.tsx`) — 4-col responsive grid of 8 account cards + 1 dashed "Custom login" tile. Each card: mono username + tier label + one-line note. Selected card = `border-primary` + `ring-3 ring-accent` + `CheckCircle2` icon. Click = fill Tenant/Username/Password fields.
- Behavior unchanged: submit success → `router.push('/me')`; error line unchanged (`text-destructive`).
- Mobile: grid collapses to single column, brand panel above form; picker → 2 cols then 1 col.

**2B. `/me` — identity hero + dashboard.**

- **Identity hero card:** `bg-card`, `rounded-lg`, `p-6`. 56px gradient avatar (initials from username), title `{role_label}: {username}`, tenant subtitle, right-aligned tenant-logo placeholder tile. Divider. 3-col meta grid: Max clearance (`ClearanceBadge`), Departments (comma-joined), Tier.
- **Actions row:** "Open chat" (primary), "View audit log" (secondary, role-gated), "Sign out" (outline, hover → destructive). These are page CTAs, not nav — TopNav provides navigation.
- **Lower grid `1fr 1.15fr` (mobile stacks):**
  - **Left — RecentQueries** (`frontend/app/me/components/RecentQueries.tsx`): list of the user's last 5 `/chat/ask` calls (mono timestamp, `CornerDownRight` icon, ellipsized query text). Data source: `GET /me/recent-queries?limit=5` (see §3).
  - **Right — DemoQuestions** (`frontend/app/me/components/DemoQuestions.tsx`): 3 "Try a demo question" cards seeded by the user's primary department (icon tile + mono category + question + `ArrowRight`, hover `translateX(2px)`). Content hardcoded in a map: `{ hr: [...], engineering: [...], security: [...], fleet_operations: [...], procurement: [...], it: [...] }`. Clicking a card navigates to `/chat` with the question prefilled via query param (`?q=...`, decoded on the chat page).

**2C. `/chat` — hero components (the money shots).**

- **CitationCard hero** ([frontend/app/chat/components/CitationCard.tsx](../../../frontend/app/chat/components/CitationCard.tsx)): `rounded-lg`, hover lift (`translateY(-2px)` + soft shadow). `id="cite-{n}"` preserved. Top row: numbered chip (`bg-primary text-primary-foreground rounded-md w-6 h-6 grid place-items-center` mono) on the left, `ClearanceBadge` on the right. Mono metadata line: dept · date. Title (14px/600). Snippet (14.5px/1.6). "View source ↗" in `text-primary` mono at the bottom.
- **ConflictCard hero** ([frontend/app/chat/components/ConflictCard.tsx](../../../frontend/app/chat/components/ConflictCard.tsx)): conflict-border, `rounded-lg`. Header bar (`bg-conflict-bg`): `GitCompareArrows` icon + subject + "2 SOURCES" pill. Body: CSS grid `1fr 60px 1fr` (mobile: stacks vertically, VS node becomes a horizontal divider). Left panel: citation chip + `ClearanceBadge` + source, contradicting phrase wrapped in `<mark>` with clearance-tinted background. Center spine: vertical 1px hairline + absolutely-positioned 40px circular "VS" node (conflict-outlined, shadowed). Right panel: `bg-[oklch(0.992_0.004_247)]` tint, mirror structure. Footer (`bg-muted`): `Scale` icon + "Holocron's read:" summary text.
- **RefusalNote hero** ([frontend/app/chat/components/RefusalNote.tsx](../../../frontend/app/chat/components/RefusalNote.tsx)): official-not-alarming. Dashed `border-border-strong` on `bg-muted`, `rounded-lg`. Left: 40px accent circle with `Lock` icon. Middle: heading "Some matches are above your clearance" + body "{N} higher-clearance sources may also be relevant." Right: mono "REF #…" + outline "Request access" button (hover → primary). Notion/Linear-permission voice, not siren voice.
- **Empty state hero** (`frontend/app/chat/components/EmptyState.tsx` — new): centered 48px accent tile with `Sparkles`, "What can the archive answer for you?" (23px/600), one-line subtitle. 3-col grid (mobile: 1 col) of demo-question cards (Compliance / Conflict detection / Clearance — icon tile + mono category + question + "Try it →"). Below: input mock — bordered `rounded-lg` field + dark Send button. Replaces the current two raw `<button>` chips.
- **MessageAssistant header:** 28px primary tile with `Sparkles` + "Holocron" + mono run "N sources · N conflict · N.Ns" (reuses the latency the audit event already writes; frontend computes from response `latency_ms`).

**2D. `/admin/audit` — summary stats + real data-table.**

- **Summary stats row:** 3 cards — Queries today (`Activity` icon, accent tile), Refusals today (`Lock`, restricted tile), Conflicts today (`GitCompareArrows`, conflict tile). Data source: `GET /admin/audit/summary` (see §3).
- **Filter bar rebuild** ([frontend/app/admin/audit/components/AuditFilters.tsx](../../../frontend/app/admin/audit/components/AuditFilters.tsx)): replace form layout with chip/segmented-control bar. Refusals segmented "All | Refusals" (active = restricted). Conflicts segmented "All | Conflicts". Date-range chip with `Calendar` icon. "Clear" link right-aligned. Backing filter state (`has_refusal`, `has_conflict`, `start`, `end`) unchanged.
- **DataTable primitive** (`frontend/app/admin/audit/components/DataTable.tsx` — new): CSS-grid-based, `bg-card`, `rounded-lg`, `overflow-hidden`. Mono uppercase header row on `bg-muted`. Columns: `150px 1.4fr 90px 90px 90px 40px` (Time · User · Latency · Refusal · Conflict · ⌄). Zebra rows via `even:bg-[oklch(0.988_0.003_247)]`. Row hover `bg-muted`. Expand chevron animates on click. User cell has an initials avatar.
- **Row expand → AuditEventDetail rework** ([frontend/app/admin/audit/components/AuditEventDetail.tsx](../../../frontend/app/admin/audit/components/AuditEventDetail.tsx)): RESPONSE event = green `PUBLIC`-style badge + mono "retrieved N · withheld N · N.Ns" + Query and Response blocks. REFUSAL event = amber badge + ref # + Withheld block.
- **"Load more" → shadcn `Button`** with `ChevronDown` icon.
- **Empty state:** centered icon + "No audit rows for the current filter." replacing the bare `<td>` message.
- **Mobile:** wrap DataTable in horizontal-scroll container with `min-w-[720px]` — upgrades Pass 1's `<table>` shim.

**Pass 2 verification.** `pnpm build` clean · manual walk of every route · screenshot every hero (login focused + demo picker, /me dashboard, /chat with citation + conflict + refusal, /chat empty state, /admin/audit summary + expanded row) · new backend tests green · full backend suite (181 tests) still green.

## 3. New backend endpoints (Pass 2 dependency)

Two pure read-only endpoints on `audit_events`. No new tables, no schema changes.

### 3.1 `GET /me/recent-queries?limit=5`

Returns the current user's last N `response`-type audit events, newest first.

- **Auth:** any logged-in user; reads own data only (`WHERE tenant_id = ... AND user_id = ...`).
- **Query params:** `limit: int = 5` (max 20, enforced).
- **Response:** `{ items: [{ correlation_id: UUID, query: str, occurred_at: datetime, latency_ms: int | null }] }`.
- **Router:** `backend/app/routers/user.py` (new file) or bolted onto `auth.py` — implementer's call.
- **Test:** one row per user, other-tenant/other-user rows excluded, limit clamped.

### 3.2 `GET /admin/audit/summary`

Returns today's counts (UTC day boundary, matching `audit_events.created_at`).

- **Auth:** role-gated `director` or `executive` (reuse the existing dep from `GET /admin/audit`).
- **Response:** `{ queries_today: int, refusals_today: int, conflicts_today: int }`.
  - `queries_today` = count of distinct `correlation_id` with `event_type='response'` today.
  - `refusals_today` = count of distinct `correlation_id` with `event_type='refusal'` today.
  - `conflicts_today` = count of distinct `correlation_id` where `event_type='response'` AND response payload has `conflicts` non-empty today. Implementation reads the JSON payload; if that becomes a hotspot, promote to a real column in a future phase.
- **Router:** add to `backend/app/routers/admin.py` next to the existing viewer endpoint.
- **Test:** count boundary (rows at 00:00 UTC included, 23:59:59 previous day excluded), tenant isolation, role gate.

Estimated ~40 LOC per endpoint including tests.

## 4. Out of scope

Deferred to Phase F / post-MVP or explicitly cut:

- **Dark mode** — deleted, not deferred. `.dark` block removed from `globals.css` in Pass 1.
- API contracts other than §3.1 and §3.2.
- Routing structure (5 routes stays 5 routes; `/` still redirects to `/me`).
- Auth flow.
- Backend behavior of any kind other than §3.
- New frontend or backend dependencies (`lucide-react`, shadcn primitives, Base UI already installed).
- Frontend test framework (Vitest/Playwright) — verification remains `pnpm build` + manual browser walk-through, matching current Phase A–D convention.
- Streaming chat responses (SSE) — Phase F, needs its own design pass.
- Conflict-card mobile-rotation animation polish (mobile stacks the split, but the VS-node rotation animation is out).

## 5. Conventions

- **Icon library:** `lucide-react`. No emoji, no inline SVG unless there is no lucide equivalent.
- **Radius:** `rounded-sm/md/lg` mapped to `--r-sm/md/lg`. No `rounded-2xl`, no bare `rounded`. Chat bubbles, cards, dialogs → `rounded-lg`. Buttons, inputs, wells → `rounded-md`. Chips, small tiles → `rounded-sm`.
- **Color usage:** semantic tokens only in TSX (`bg-card`, `text-muted-foreground`, `border-border`, `bg-accent`, `text-primary`, `bg-public`, etc.). Hard-coded `oklch(...)` allowed only for two site-local shades the handoff prescribes: right conflict panel tint (`oklch(0.992 0.004 247)`) and zebra table row (`oklch(0.988 0.003 247)`).
- **Typography:** Geist Sans by default; Geist Mono for metadata (dept · date · ref # · timestamps · latency · mono uppercase labels). Body 14–15px / line-height 1.6. Mono metadata 10–11px / 600 / tracking 0.06–0.1em.
- **File layout:** shared primitives → `frontend/components/*.tsx`. Route-local components → `frontend/app/{route}/components/*.tsx`.

## 6. Verification

**After Pass 1 merge:**

- `pnpm build` clean.
- Every route renders — no visual regression, just unification.
- `grep -rE "slate-|gray-" frontend/app frontend/components` returns zero hits in TSX files.
- `.dark` block absent from `frontend/app/globals.css`.
- `TopNav` renders on `/me`, `/chat`, `/admin/audit` with correct active state; "Audit log" tab hidden for employees and managers.
- Mobile viewport (375px width) doesn't break any route.

**After Pass 2 merge:**

- `pnpm build` clean.
- Manual walk of every route.
- Screenshots captured for portfolio: login (focused field + demo picker selected), /me (identity hero + recent queries + demo cards), /chat (citation grid + conflict card + refusal note), /chat empty state, /admin/audit (summary row + expanded row).
- Two new backend endpoints have passing tests; full backend suite (181 tests) still green — Phase E must not regress backend tests.

## 7. Deviations from the design handoff

The handoff was written provider-agnostic. Concrete decisions from the Phase E brainstorm:

- **Dark mode removed** rather than deferred. `.dark` block deleted from `globals.css` outright.
- **Two additive backend endpoints** added (§3) to power `/me` Recent queries and `/admin/audit` summary stats. Handoff said "no API changes"; we're breaking that intentionally, scope-boxed to reads on `audit_events`.
- **Numbered as Phase E.** The "Deferred to Phase E / post-MVP" bucket in CLAUDE.md becomes **Phase F** in this session.
- **Phase D nav-fix commits (`ace4485`, `8e14594`) become partially dead code** once TopNav ships in Pass 1 — the ad-hoc `/me` "Open chat" / "View audit log" buttons remain (they're page CTAs, not nav), but the fix's role of "prevent dead-end" is now owned by TopNav.
- **Demo-question cards seeded by department, not just role.** Handoff said "seeded by role"; the interesting variance is by department (executive.fleet vs executive.procurement should see different suggestions). Implementation maps by primary department; falls back to a default set if department has no map entry.

## 8. Files & routes affected

**Modified:**

- `frontend/app/globals.css` (tokens, radius scale, remove `.dark`)
- `frontend/tailwind.config.ts` (expose new tokens)
- `frontend/components/ClearanceBadge.tsx` + `frontend/lib/clearance-color.ts` (semantic tokens)
- `frontend/app/login/page.tsx` (Pass 2 layout)
- `frontend/app/me/page.tsx` (Pass 2 dashboard)
- `frontend/app/chat/page.tsx` (mobile spacing; empty state swap)
- `frontend/app/chat/components/*.tsx` (all 7 components touched: token migration in Pass 1, hero rewrites in Pass 2)
- `frontend/app/admin/audit/page.tsx` (data-table integration)
- `frontend/app/admin/audit/components/*.tsx` (filter bar + event detail rework; audit row consumed by DataTable)
- `frontend/app/admin/layout.tsx` (insert TopNav)
- CLAUDE.md (Phase E section added; existing "Deferred to Phase E" → "Deferred to Phase F")

**New:**

- `frontend/components/TopNav.tsx`
- `frontend/components/CitationChip.tsx`
- `frontend/app/login/components/DemoAccountPicker.tsx`
- `frontend/app/me/components/RecentQueries.tsx`
- `frontend/app/me/components/DemoQuestions.tsx`
- `frontend/app/chat/components/EmptyState.tsx`
- `frontend/app/admin/audit/components/DataTable.tsx`
- `backend/app/routers/user.py` (or extension to `auth.py`)
- Backend tests for `/me/recent-queries` and `/admin/audit/summary`

**Routes:** unchanged surface (`/`, `/login`, `/me`, `/chat`, `/admin/audit`). `/` still redirects to `/me`.

## 9. Non-functional notes

- **Verification of Tailwind changes must use `pnpm build`, not `tsc --noEmit`.** Documented in CLAUDE.md as a Phase D lesson.
- **`pnpm approve-builds --all`** on fresh installs (sharp + unrs-resolver) — no change from current setup.
- **No new native deps** — Phase E adds no packages.
- **shadcn token bridge** in `tailwind.config.ts` (added in Phase D) is load-bearing; Pass 1's config changes extend it, don't replace it.
- **Backend warmup** unchanged: FastAPI lifespan still warms BGE + spaCy; `HOLOCRON_SKIP_WARMUP=1` still bypasses.
- **Corpus, seed scripts, eval harness** untouched.

## 10. Success criteria

Phase E is complete when:

1. Both passes merged to `main` and pushed to GitHub.
2. All 4 authenticated routes render with the design system: unified tokens, unified radii, no `slate-*`/`gray-*` leaks, lucide icons only, mobile-friendly.
3. Persistent TopNav on `/me`, `/chat`, `/admin/audit` — no dead-end pages.
4. Portfolio screenshots captured of all 4 hero components (CitationCard, ConflictCard, RefusalNote, empty state) and both dashboard surfaces (/me, /admin/audit).
5. Backend tests still 181+ green (adds ~2 for new endpoints).
6. CLAUDE.md updated: Phase E section marks ✅; former "Deferred to Phase E" bucket renamed to Phase F.

Phase E is **not** blocked on:

- Any Phase F item (they were deferred deliberately).
- Additional design work — the handoff is the source of visual truth.
- Dark mode (out of scope).
