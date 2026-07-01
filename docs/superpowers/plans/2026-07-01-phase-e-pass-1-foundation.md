# HOLOCRON Phase E — Pass 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the foundation of the frontend revamp — seed tokens, expose them in Tailwind, unify radii, migrate every `slate-*`/`gray-*` utility to semantic tokens, drop the two emoji for lucide icons, ship the `TopNav` primitive, polish `ClearanceBadge` + `CitationChip`, and add mobile breakpoints to all 4 routes. Zero visual regression; every route should look the same or slightly more unified after this pass merges.

**Architecture:** Bottom-up. Tokens land first, then Tailwind config exposes them as utilities, then component code migrates to use them. Two new primitives (`TopNav`, `CitationChip`) plug into the existing routes without touching product behavior. Verification per task is `pnpm build` + a scoped grep + a browser check — no test framework.

**Tech Stack:** Next.js 15.0.0 App Router · React 19 RC · TypeScript · Tailwind 3.4.19 · shadcn/ui · lucide-react (already installed).

**Design source of truth:** `handoffs/design_handoff_holocron_frontend/README.md` (gitignored, local-only). Token oklch values in the "Design Tokens" section of that README.

**Verification convention (all tasks):**

- `pnpm build` must produce a clean production build. Do NOT rely on `tsc --noEmit` — it misses Tailwind class-generation failures (documented Phase D lesson in CLAUDE.md).
- Frontend has no test framework. "Test" for each task is: build clean · targeted grep must produce expected result · manual browser check of the affected route.
- Commit after each task using the repo's `type(scope): message` convention.

---

## Prerequisites

- [ ] **Check current branch is `phase-e`.**

Run: `git branch --show-current`
Expected: `phase-e`

If not on phase-e: `git checkout phase-e`. This branch was created during brainstorming (session 2026-07-01).

- [ ] **Verify frontend dev environment.**

Run from repo root:
```
cd frontend
pnpm install
pnpm build
```
Expected: build completes successfully. If `sharp` or `unrs-resolver` complain about needing approval, run `pnpm approve-builds --all` and retry `pnpm build`.

If the build fails at this point, STOP and diagnose — the migration must start from a working baseline.

- [ ] **Grep the migration baseline.**

Run from repo root: `git grep -nE "slate-|gray-" -- frontend/app frontend/components`
Expected: **48 total occurrences across 16 files** (baseline as of session 2026-07-01). If your count differs, that's fine — record whatever number you see; the goal at the end of Pass 1 is `0`.

---

## Task 1: Seed tokens and delete the `.dark` block in `globals.css`

**Files:**
- Modify: `frontend/app/globals.css`

**Goal:** Add the new tokens (`--surface`, `--border-strong`, `--subtle`, radius scale, clearance/conflict groups), overwrite existing shadcn defaults with the handoff's oklch values, and delete the entire `.dark` block. `--font-sans` bridge and the `* { border-color / outline-color }` block from Phase D stay intact.

- [ ] **Step 1: Replace the `:root` block and delete `.dark`.**

Open `frontend/app/globals.css`. Replace lines 14–143 (the entire `:root { ... }` block plus the entire `.dark { ... }` block) with the following. Keep lines 1–13 (the `@import`/`@tailwind` stack and `.theme` block) and lines 144–158 (the `* {}`, `body {}`, `html {}` blocks) exactly as they are.

New `:root` block:

```css
  :root {
    /* Neutrals & brand (Phase E — handoff oklch values) */
    --background: oklch(0.984 0.003 247);
    --foreground: oklch(0.205 0.014 257);
    --surface: oklch(0.976 0.004 247);           /* NEW — chat thread bg, panel wells */
    --card: oklch(1 0 0);
    --card-foreground: oklch(0.205 0.014 257);
    --popover: oklch(1 0 0);
    --popover-foreground: oklch(0.205 0.014 257);
    --primary: oklch(0.47 0.13 264);              /* corporate indigo */
    --primary-foreground: oklch(0.985 0.004 247);
    --secondary: oklch(0.967 0.004 247);
    --secondary-foreground: oklch(0.205 0.014 257);
    --muted: oklch(0.967 0.004 247);
    --muted-foreground: oklch(0.53 0.013 257);
    --subtle: oklch(0.62 0.012 257);              /* NEW — mono metadata, labels */
    --accent: oklch(0.955 0.022 264);
    --accent-foreground: oklch(0.42 0.12 264);
    --destructive: oklch(0.577 0.245 27.325);
    --border: oklch(0.916 0.006 247);
    --border-strong: oklch(0.86 0.008 247);       /* NEW — inputs, hover borders */
    --input: oklch(0.916 0.006 247);
    --ring: oklch(0.47 0.13 264);

    /* Semantic — clearance & state (Phase E — reserved for meaning, never decoration) */
    --public-bg: oklch(0.952 0.045 152);
    --public-fg: oklch(0.43 0.085 152);
    --public-border: oklch(0.86 0.06 152);
    --restricted-bg: oklch(0.964 0.05 85);
    --restricted-fg: oklch(0.5 0.1 72);
    --restricted-border: oklch(0.88 0.07 85);
    --secret-bg: oklch(0.95 0.045 25);
    --secret-fg: oklch(0.52 0.16 25);
    --secret-border: oklch(0.88 0.06 25);
    --top-secret-bg: oklch(0.32 0.09 25);
    --top-secret-fg: oklch(0.95 0.02 25);
    --top-secret-border: oklch(0.26 0.08 25);
    --conflict-bg: oklch(0.972 0.022 25);
    --conflict-fg: oklch(0.5 0.17 25);
    --conflict-border: oklch(0.86 0.06 25);

    /* Charts — retained (unchanged from Phase D scaffold) */
    --chart-1: oklch(0.87 0 0);
    --chart-2: oklch(0.556 0 0);
    --chart-3: oklch(0.439 0 0);
    --chart-4: oklch(0.371 0 0);
    --chart-5: oklch(0.269 0 0);

    /* Legacy shadcn radius var kept for compatibility with pre-existing UI */
    --radius: 0.625rem;

    /* Radius scale (Phase E — chips/inputs/cards) */
    --r-sm: 8px;
    --r-md: 10px;
    --r-lg: 14px;

    /* Sidebar — retained from Phase D scaffold; not used by Phase E surfaces */
    --sidebar: oklch(0.985 0 0);
    --sidebar-foreground: oklch(0.145 0 0);
    --sidebar-primary: oklch(0.205 0 0);
    --sidebar-primary-foreground: oklch(0.985 0 0);
    --sidebar-accent: oklch(0.97 0 0);
    --sidebar-accent-foreground: oklch(0.205 0 0);
    --sidebar-border: oklch(0.922 0 0);
    --sidebar-ring: oklch(0.708 0 0);
  }
  /* .dark block removed (Phase E, per spec §4 out-of-scope). */
```

- [ ] **Step 2: Verify build after the swap.**

Run from `frontend/`: `pnpm build`
Expected: build succeeds. If it fails with a CSS parse error, check that lines 1–13 and 144–158 of `globals.css` are still present and untouched.

- [ ] **Step 3: Verify `.dark` is gone.**

Run from `frontend/`: `grep -n "\.dark" app/globals.css || echo NONE`
Expected: `NONE`.

- [ ] **Step 4: Manual browser check.**

Start the dev server (`pnpm dev`) and visit `/login`. It should render — background should now be a slightly warm neutral (light indigo cast), not pure white. Text should be dark neutral. That's the new baseline. Stop the dev server.

- [ ] **Step 5: Commit.**

```
git add frontend/app/globals.css
git commit -m "feat(frontend): seed Phase E design tokens; drop dark block

- Add oklch neutrals (--surface, --subtle, --border-strong).
- Add semantic clearance/conflict groups (public/restricted/secret/top-secret/conflict).
- Add radius scale (--r-sm/md/lg).
- Retint --primary to corporate indigo per handoff.
- Delete .dark block (Phase E out of scope; can be re-added by a future
  Phase F pass with its own dark hero specs)."
```

---

## Task 2: Extend `tailwind.config.ts` to expose new tokens

**Files:**
- Modify: `frontend/tailwind.config.ts`

**Goal:** Register the new `--surface`, `--border-strong`, `--subtle`, radius scale (`--r-*`), and semantic clearance/conflict groups as Tailwind utilities so components can write `bg-surface`, `border-border-strong`, `bg-public`, `bg-conflict-bg`, etc.

- [ ] **Step 1: Replace the `theme.extend` block.**

Open `frontend/tailwind.config.ts`. Replace the entire `theme: { extend: { ... } }` block (currently lines 9–58) with:

```ts
  theme: {
    extend: {
      colors: {
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: "var(--surface)",
        subtle: "var(--subtle)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        // Semantic clearance/state — reserved for meaning; never decoration.
        public: {
          DEFAULT: "var(--public-bg)",
          foreground: "var(--public-fg)",
          border: "var(--public-border)",
        },
        restricted: {
          DEFAULT: "var(--restricted-bg)",
          foreground: "var(--restricted-fg)",
          border: "var(--restricted-border)",
        },
        secret: {
          DEFAULT: "var(--secret-bg)",
          foreground: "var(--secret-fg)",
          border: "var(--secret-border)",
        },
        "top-secret": {
          DEFAULT: "var(--top-secret-bg)",
          foreground: "var(--top-secret-fg)",
          border: "var(--top-secret-border)",
        },
        conflict: {
          DEFAULT: "var(--conflict-bg)",
          foreground: "var(--conflict-fg)",
          border: "var(--conflict-border)",
        },
      },
      borderRadius: {
        // Phase E radius scale (--r-sm/md/lg on top of legacy --radius).
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans, var(--font-sans))"],
        mono: ["var(--font-geist-mono)"],
      },
    },
  },
```

- [ ] **Step 2: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: build succeeds. If Tailwind complains about class generation, verify the color object keys match (`"border-strong"`, `"top-secret"` — dashed names must be quoted).

- [ ] **Step 3: Smoke-check the new utilities exist.**

Add a temporary probe to `frontend/app/login/page.tsx` — anywhere in the JSX — like `<div className="bg-surface bg-public bg-conflict-bg border-border-strong rounded-lg rounded-md rounded-sm" />`. Run `pnpm build`. Expected: build succeeds and generated CSS contains rules for those classes. Then **remove** the probe.

- [ ] **Step 4: Commit.**

```
git add frontend/tailwind.config.ts
git commit -m "feat(frontend): expose Phase E tokens as Tailwind utilities

Adds --surface, --subtle, --border-strong, --r-sm/md/lg, and the semantic
clearance/conflict color groups (public/restricted/secret/top-secret/conflict)
to theme.extend. Enables bg-surface, border-border-strong, bg-public,
bg-conflict-bg, rounded-sm/md/lg utilities."
```

---

## Task 3: Migrate the two emoji to lucide-react icons

**Files:**
- Modify: `frontend/app/chat/components/RefusalNote.tsx`
- Modify: `frontend/app/chat/components/MessageAssistant.tsx`

**Goal:** Replace 🔒 in `RefusalNote` with `<Lock />` and ⚠ in `MessageAssistant` with `<TriangleAlert />`. Small isolated change.

- [ ] **Step 1: Update `RefusalNote.tsx`.**

Overwrite `frontend/app/chat/components/RefusalNote.tsx` with:

```tsx
import { Lock } from "lucide-react";
import { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  return (
    <div className="p-3 bg-slate-50 border border-dashed border-slate-400 rounded-lg text-xs text-slate-600 flex items-start gap-2">
      <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden />
      <div>
        <strong>{refusal.withheld_count} higher-clearance source(s) may also be relevant.</strong>{" "}
        Request access via Reference{" "}
        <code className="bg-slate-200 px-1 py-0.5 rounded text-[11px]">
          #{refusal.reference_id}
        </code>
        .
      </div>
    </div>
  );
}
```

Note: `slate-*` classes are still here — they're removed in Task 6. This task is icons-only.

- [ ] **Step 2: Update `MessageAssistant.tsx` conflict header.**

In `frontend/app/chat/components/MessageAssistant.tsx`, add `TriangleAlert` to the imports and swap the emoji in the "Conflicts detected" heading. Replace the top of the file:

```tsx
import React from "react";
import { TriangleAlert } from "lucide-react";
import { ChatResponse } from "@/lib/types/chat";
import { CitationCard } from "./CitationCard";
import { ConflictCard } from "./ConflictCard";
import { RefusalNote } from "./RefusalNote";
```

Then replace the conflict-section header line (currently `<div className="text-[10px] uppercase tracking-wider text-red-700 mb-1.5">⚠ Conflicts detected · {payload.conflicts.length}</div>`) with:

```tsx
          <div className="text-[10px] uppercase tracking-wider text-red-700 mb-1.5 flex items-center gap-1">
            <TriangleAlert className="w-3 h-3" aria-hidden />
            Conflicts detected · {payload.conflicts.length}
          </div>
```

- [ ] **Step 3: Verify build + no emoji leaks.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

Run from `frontend/`: `grep -rE "🔒|⚠" app components || echo NONE`
Expected: `NONE`.

- [ ] **Step 4: Manual browser check.**

Start `pnpm dev`. Log in as `employee.security` / `imperial-march`, ask "What's the dress-code policy for off-base events?" — that produces a refusal. Confirm the padlock lucide icon appears next to the text. Stop dev server.

- [ ] **Step 5: Commit.**

```
git add frontend/app/chat/components/RefusalNote.tsx frontend/app/chat/components/MessageAssistant.tsx
git commit -m "feat(frontend): replace emoji with lucide icons in refusal + conflict headers

- RefusalNote: Lock icon (was 🔒)
- MessageAssistant: TriangleAlert next to 'Conflicts detected' (was ⚠)"
```

---

## Task 4: Migrate `ClearanceBadge` to semantic tokens

**Files:**
- Modify: `frontend/lib/clearance-color.ts`
- Modify: `frontend/components/ClearanceBadge.tsx`

**Goal:** Replace hard-coded `green-*`/`amber-*`/`red-*` in `clearanceBadgeClasses` with the new semantic utilities (`bg-public`, `text-public-foreground`, `border-public-border`, etc.). Tighten the badge to mono 11px/600, `0.07em` tracking, dot + label pattern per handoff.

- [ ] **Step 1: Update `clearance-color.ts`.**

Overwrite `frontend/lib/clearance-color.ts` with:

```ts
import { Clearance } from "@/lib/types/chat";

export function clearanceBadgeClasses(c: Clearance): string {
  switch (c) {
    case "public":
      return "bg-public text-public-foreground border-public-border";
    case "restricted":
      return "bg-restricted text-restricted-foreground border-restricted-border";
    case "secret":
      return "bg-secret text-secret-foreground border-secret-border";
    case "top_secret":
      return "bg-top-secret text-top-secret-foreground border-top-secret-border";
  }
}

export function clearanceLabel(c: Clearance): string {
  switch (c) {
    case "public": return "PUBLIC";
    case "restricted": return "RESTRICTED";
    case "secret": return "SECRET";
    case "top_secret": return "TOP SECRET";
  }
}

/** Dot color for the badge's leading dot. Matches the fg color for contrast. */
export function clearanceDotClasses(c: Clearance): string {
  switch (c) {
    case "public": return "bg-public-foreground";
    case "restricted": return "bg-restricted-foreground";
    case "secret": return "bg-secret-foreground";
    case "top_secret": return "bg-top-secret-foreground";
  }
}
```

- [ ] **Step 2: Update `ClearanceBadge.tsx`.**

Overwrite `frontend/components/ClearanceBadge.tsx` with:

```tsx
import { clearanceBadgeClasses, clearanceDotClasses, clearanceLabel } from "@/lib/clearance-color";
import { Clearance } from "@/lib/types/chat";

export function ClearanceBadge({ classification }: { classification: Clearance }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[11px] font-mono font-semibold tracking-[0.07em] border ${clearanceBadgeClasses(classification)}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${clearanceDotClasses(classification)}`} aria-hidden />
      {clearanceLabel(classification)}
    </span>
  );
}
```

- [ ] **Step 3: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 4: Manual browser check.**

Start `pnpm dev`. Log in as `executive.procurement`. On `/me`, the SECRET badge next to "Max clearance:" should now be mono-typography with a leading dot. Colors should still read as red-ish for SECRET; the palette shifted slightly per handoff. Stop dev server.

- [ ] **Step 5: Commit.**

```
git add frontend/lib/clearance-color.ts frontend/components/ClearanceBadge.tsx
git commit -m "feat(frontend): migrate ClearanceBadge to semantic tokens + mono type

- clearance-color.ts: switch from hard-coded green/amber/red to
  bg-public / bg-restricted / bg-secret / bg-top-secret semantic groups.
- ClearanceBadge: mono 11px/600, 0.07em tracking, leading dot + label pattern
  per handoff. rounded-sm (was rounded)."
```

---

## Task 5: Build the `CitationChip` primitive and swap it in

**Files:**
- Create: `frontend/components/CitationChip.tsx`
- Modify: `frontend/app/chat/components/MessageAssistant.tsx`

**Goal:** Extract the inline `[n]` chip rendering into a shared primitive with proper hover/active states, then use it in `renderAnswerText`.

- [ ] **Step 1: Create `CitationChip.tsx`.**

Create `frontend/components/CitationChip.tsx` with:

```tsx
export function CitationChip({ marker }: { marker: number }) {
  return (
    <a
      href={`#cite-${marker}`}
      className="inline-flex items-center justify-center min-w-[20px] px-1 mx-0.5 rounded-sm bg-accent text-accent-foreground font-mono text-[12px] font-semibold hover:bg-primary hover:text-primary-foreground active:bg-primary active:text-primary-foreground active:ring-[3px] active:ring-accent transition-colors"
    >
      [{marker}]
    </a>
  );
}
```

- [ ] **Step 2: Consume `CitationChip` in `MessageAssistant.tsx`.**

Update `MessageAssistant.tsx`. Add `CitationChip` to the imports:

```tsx
import { CitationChip } from "@/components/CitationChip";
```

Then replace the `renderAnswerText` function's map body. Where it currently renders an inline `<a href={`#cite-${marker}`} ... >[{marker}]</a>` with the `bg-blue-100 text-blue-800` classes, replace with:

```tsx
    return <CitationChip key={i} marker={marker} />;
```

The full updated `renderAnswerText` should look like:

```tsx
function renderAnswerText(text: string) {
  const parts = text.split(/(\[\d+\])/);
  return parts.map((token, i) => {
    const m = token.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{token}</React.Fragment>;
    const marker = parseInt(m[1], 10);
    return <CitationChip key={i} marker={marker} />;
  });
}
```

- [ ] **Step 3: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

Run from `frontend/`: `grep -n "bg-blue-100" app/chat/components/MessageAssistant.tsx || echo NONE`
Expected: `NONE` (the old blue-chip class must be gone).

- [ ] **Step 4: Manual browser check.**

Start `pnpm dev`. Log in as `executive.procurement`. Ask "What's the dress-code policy for off-base events?" The answer should render with `[1]`, `[2]` chips in accent color (soft light-indigo) rather than blue. Hover a chip — it should turn corporate-indigo with white text. Click one — it should scroll to the cited card and show the active state (indigo + accent ring). Stop dev server.

- [ ] **Step 5: Commit.**

```
git add frontend/components/CitationChip.tsx frontend/app/chat/components/MessageAssistant.tsx
git commit -m "feat(frontend): add CitationChip primitive with hover + active states

Extracts inline [n] chip from MessageAssistant.renderAnswerText into a
reusable component with three states:
- default: bg-accent / text-accent-foreground
- hover: bg-primary / text-primary-foreground
- active: bg-primary + ring-3 ring-accent"
```

---

## Task 6: Migrate `/chat` components to semantic tokens + unify radii

**Files:**
- Modify: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/chat/components/ChatThread.tsx`
- Modify: `frontend/app/chat/components/MessageUser.tsx`
- Modify: `frontend/app/chat/components/MessageAssistant.tsx`
- Modify: `frontend/app/chat/components/CitationCard.tsx`
- Modify: `frontend/app/chat/components/ConflictCard.tsx`
- Modify: `frontend/app/chat/components/RefusalNote.tsx`
- Modify: `frontend/app/chat/components/ChatInput.tsx`

**Goal:** Remove every `slate-*` class from the chat surface and replace with the token mapping table below. Unify radii while touching each file.

**Migration mapping table (use everywhere in this task):**

| Old class | New class | Notes |
|---|---|---|
| `bg-slate-800` | `bg-foreground` | user bubble bg — foreground on background inverts naturally |
| `text-white` (on user bubble) | `text-background` | pairs with `bg-foreground` |
| `bg-slate-50` (assistant bubble) | `bg-card` | card surface |
| `bg-slate-50` (refusal note bg) | `bg-muted` | well/tint |
| `bg-slate-100` / `bg-slate-200` | `bg-muted` | mono metadata backgrounds |
| `border-slate-200` | `border-border` | hairlines |
| `border-slate-400` (dashed refusal) | `border-border-strong` | stronger dashed border |
| `text-slate-400` | `text-subtle` | de-emphasized meta |
| `text-slate-500` | `text-muted-foreground` | secondary body |
| `text-slate-600` | `text-muted-foreground` | body secondary |
| `rounded-2xl` (chat bubbles) | `rounded-lg` | unified card radius |
| `rounded-tl-md` / `rounded-tr-md` / `rounded-br-md` etc. | keep as-is | asymmetric bubble corners survive the migration |
| Bare `rounded` | `rounded-md` | inputs/pills default |
| `bg-blue-100 text-blue-800` (old citation chip) | already handled in Task 5 |

- [ ] **Step 1: List every `slate-*` hit in `/chat`.**

Run from `frontend/`: `grep -nE "slate-" app/chat`
Expected: a list of files + line numbers. Compare against the file list above — all hits should live in those 8 files.

- [ ] **Step 2: Migrate each file using the mapping table.**

For each of the 8 files listed above, open the file, apply the mapping table row-by-row. Preserve behavior — this is a color/radius refactor, not a rewrite.

Special notes:
- `MessageAssistant.tsx`: the `text-red-700` conflict header stays (that's semantic, not a slate leak). It becomes `text-destructive` in a later phase; leave it for now.
- `RefusalNote.tsx`: after this migration, its container becomes `bg-muted border border-dashed border-border-strong rounded-lg text-muted-foreground`. The inner `<code>` becomes `bg-muted-foreground/10 px-1 py-0.5 rounded-sm text-[11px]` — use `rounded-sm` not `rounded` for the code chip.
- `MessageUser.tsx`: user bubble `bg-slate-800 text-white rounded-2xl rounded-br-md` → `bg-foreground text-background rounded-lg rounded-br-md`.
- `ChatInput.tsx`: has 3 slate hits; replace input container `border-slate-200` → `border-border`, textarea `focus:ring-slate-400` → `focus:ring-ring`, disabled Send button `bg-slate-400` → `bg-muted-foreground`.
- `chat/page.tsx`: 7 slate hits in the header bar + empty-state + loading state. Header `border-b border-slate-200` → `border-b border-border`. `text-slate-400` separators → `text-subtle`. `text-slate-500` → `text-muted-foreground`. `text-slate-600` → `text-muted-foreground`. Empty-state suggested-question button `border-slate-200 hover:bg-slate-50` → `border-border hover:bg-muted`.

- [ ] **Step 3: Verify no slate leaks remain in `/chat`.**

Run from `frontend/`: `grep -rE "slate-" app/chat || echo NONE`
Expected: `NONE`.

- [ ] **Step 4: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Manual browser check.**

Start `pnpm dev`. Log in as `executive.procurement`. Send a message. Verify:
- User bubble = dark foreground on card
- Assistant bubble = card white
- Citation grid renders normally, cards have `rounded-lg` corners
- Chat bubbles are `rounded-lg` (visibly a hair tighter than before if you had a screenshot)
- Refusal note (test with `employee.security` dress-code query) shows the new muted bg + dashed border + lock icon

Stop dev server.

- [ ] **Step 6: Commit.**

```
git add frontend/app/chat/page.tsx frontend/app/chat/components/
git commit -m "refactor(frontend): migrate /chat to semantic tokens + unified radii

Replace every slate-* utility across the chat surface (page.tsx + 7
components) with semantic tokens per the Phase E mapping table. Unify
bubbles from rounded-2xl to rounded-lg. No behavior change."
```

---

## Task 7: Migrate `/admin/audit` components to semantic tokens + unify radii

**Files:**
- Modify: `frontend/app/admin/layout.tsx`
- Modify: `frontend/app/admin/audit/page.tsx`
- Modify: `frontend/app/admin/audit/components/AuditFilters.tsx`
- Modify: `frontend/app/admin/audit/components/AuditRow.tsx`
- Modify: `frontend/app/admin/audit/components/AuditEventDetail.tsx`

**Goal:** Same migration but for the audit surface, which uses `gray-*` (not `slate-*`).

**Migration mapping table:**

| Old class | New class | Notes |
|---|---|---|
| `bg-gray-50` (table header) | `bg-muted` | header row well |
| `bg-gray-50` (hover) | `bg-muted` | row hover |
| `text-gray-500` | `text-muted-foreground` | secondary body |
| `text-gray-600` | `text-muted-foreground` | body secondary |
| `border-gray-*` | `border-border` | any grayscale border |
| `bg-red-50 border-red-200 text-red-700` (error banner) | `bg-destructive/10 border-destructive/40 text-destructive` | error banner using destructive token |
| Bare `rounded` (table wrapper) | `rounded-lg` | card radius |
| Bare `rounded` (Load-more button) | `rounded-md` | button radius |
| `bg-red-100 text-red-800`, `bg-amber-100 text-amber-800`, `bg-emerald-100 text-emerald-800` etc (event type badges) | `bg-restricted text-restricted-foreground` (refusal), `bg-public text-public-foreground` (response) | color-code REFUSAL=restricted amber, RESPONSE=public green per spec §2D |

- [ ] **Step 1: List every `gray-*` hit under `/admin`.**

Run from `frontend/`: `grep -nE "gray-" app/admin`
Expected: a list. All hits should live in the 5 files above.

- [ ] **Step 2: Migrate each file using the mapping table.**

Special notes:
- `admin/layout.tsx`: `text-gray-500` loading state → `text-muted-foreground`. Access-denied `text-red-700` → `text-destructive`.
- `admin/audit/page.tsx`: description `text-gray-600` → `text-muted-foreground`. Error banner `border-red-200 bg-red-50 text-red-700 rounded p-3` → `border-destructive/40 bg-destructive/10 text-destructive rounded-md p-3`. Table wrapper `border rounded overflow-hidden` → `border border-border rounded-lg overflow-hidden`. `thead bg-gray-50` → `bg-muted`. Empty-state `text-gray-500` → `text-muted-foreground`. Load-more button `border rounded hover:bg-gray-50` → `border border-border rounded-md hover:bg-muted`.
- `AuditFilters.tsx`: 6 gray hits. Filter chip inline styles: labels `text-gray-600` → `text-muted-foreground`; inputs `border-gray-300` → `border-border-strong`; clear-link `text-gray-500` → `text-muted-foreground`.
- `AuditRow.tsx`: 4 gray hits. Row hover `hover:bg-gray-50` → `hover:bg-muted`. Latency mono `text-gray-500` → `text-muted-foreground`. YES/NO pills for Refusal/Conflict — leave amber/red palette as-is until Task 11 (they map to semantic clearance/conflict tokens as a later polish, not this pass).
- `AuditEventDetail.tsx`: 5 gray hits. Container `bg-gray-50 border-gray-200 rounded p-3` → `bg-muted border border-border rounded-md p-3`. Section labels `text-gray-500` → `text-muted-foreground`. Type badges: refusal `bg-amber-100 text-amber-800` → `bg-restricted text-restricted-foreground`; response `bg-emerald-100 text-emerald-800` (if present) → `bg-public text-public-foreground`.

- [ ] **Step 3: Verify no gray leaks remain in `/admin`.**

Run from `frontend/`: `grep -rE "gray-" app/admin || echo NONE`
Expected: `NONE`.

- [ ] **Step 4: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Manual browser check.**

Start `pnpm dev`. Log in as `executive.procurement`. Navigate to `/admin/audit`. Verify:
- Page renders normally, table shows any prior audit rows
- Table wrapper has `rounded-lg` corners
- Header row uses muted bg
- Click a row to expand — event detail card should show restricted (amber) badge for REFUSAL, public (green) badge for RESPONSE
- Load-more button (if visible) uses new border-border style

Stop dev server.

- [ ] **Step 6: Commit.**

```
git add frontend/app/admin/
git commit -m "refactor(frontend): migrate /admin to semantic tokens + unified radii

Replace every gray-* utility across the admin surface (layout + audit
page + 3 components) with semantic tokens per the Phase E mapping table.
Event-type badges now consume the semantic clearance groups (refusal=
restricted amber, response=public green). Table wrapper rounded-lg."
```

---

## Task 8: Migrate `/login` and `/me` to semantic tokens

**Files:**
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/me/page.tsx`

**Goal:** Same migration but for the auth-adjacent surfaces. `/login` has 1 slate hit; `/me` has 2 slate hits.

**Migration mapping table:** same as Task 6.

- [ ] **Step 1: List every `slate-*` hit under `/login` and `/me`.**

Run from `frontend/`: `grep -nE "slate-" app/login app/me`
Expected: 3 hits total (1 in `/login`, 2 in `/me`).

- [ ] **Step 2: Migrate each file.**

- `login/page.tsx`: swap the one `text-slate-*` line (an error/hint line) to `text-muted-foreground` or `text-destructive` as appropriate — check whether it's an error-red line or a neutral hint before choosing.
- `me/page.tsx`: `text-sm text-slate-500` (twice — "Max clearance:" label and "Departments" label) → `text-sm text-muted-foreground`.

- [ ] **Step 3: Verify no slate leaks remain in `/login` or `/me`.**

Run from `frontend/`: `grep -rE "slate-" app/login app/me || echo NONE`
Expected: `NONE`.

- [ ] **Step 4: Verify full-app slate/gray sweep is clean.**

Run from `frontend/`: `grep -rE "slate-|gray-" app components || echo NONE`
Expected: `NONE` — the only remaining `gray-` hit anywhere is in `components/ui/button.tsx` (shadcn library file, not app code). If that one shows up, it's fine to leave — it's vendor-owned.

Actually, verify the button hit: `grep -nE "gray-" components/ui/button.tsx`. If it's just one line inside a shadcn variant, leave it (shadcn owns that file). If it's more, sweep it too using the mapping table.

- [ ] **Step 5: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 6: Manual browser check.**

Start `pnpm dev`. Log out. Visit `/login`. Enter a bad password on purpose — the error hint should render (either muted or destructive-red depending on which class you kept). Log in as `executive.procurement`. Visit `/me`. The "Max clearance:" and "Departments" labels should render in muted foreground color, badge unchanged.

Stop dev server.

- [ ] **Step 7: Commit.**

```
git add frontend/app/login/page.tsx frontend/app/me/page.tsx frontend/components/ui/button.tsx
git commit -m "refactor(frontend): migrate /login and /me to semantic tokens

Completes the slate/gray sweep. Pass 1's migration is now complete —
zero slate-*/gray-* utilities in app/ or components/ (excluding
vendor-owned shadcn files where migration is inappropriate)."
```

If the shadcn Button file didn't need changes, drop it from the `git add`.

---

## Task 9: Build the `TopNav` primitive

**Files:**
- Create: `frontend/components/TopNav.tsx`

**Goal:** A persistent 62px nav bar for authenticated routes. Left: HOLOCRON wordmark + tab links (Home / Chat / Audit log) with active-state underline. Right: ClearanceBadge + initials avatar. Audit tab role-gated to `director`/`executive`. Not rendered on `/login`.

- [ ] **Step 1: Create `TopNav.tsx`.**

Create `frontend/components/TopNav.tsx` with:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database } from "lucide-react";

import { ClearanceBadge } from "@/components/ClearanceBadge";
import type { Clearance } from "@/lib/types/chat";

export interface TopNavUser {
  username: string;
  role: string;
  max_clearance: Clearance;
}

interface TabDef {
  href: string;
  label: string;
  match: (pathname: string) => boolean;
  requiresAdmin?: boolean;
}

const TABS: TabDef[] = [
  { href: "/me", label: "Home", match: (p) => p === "/me" || p === "/" },
  { href: "/chat", label: "Chat", match: (p) => p.startsWith("/chat") },
  { href: "/admin/audit", label: "Audit log", match: (p) => p.startsWith("/admin"), requiresAdmin: true },
];

function initials(username: string): string {
  const [head, tail] = username.split(".");
  const first = head?.[0] ?? "";
  const second = tail?.[0] ?? head?.[1] ?? "";
  return (first + second).toUpperCase() || "?";
}

export function TopNav({ user }: { user: TopNavUser }) {
  const pathname = usePathname();
  const isAdmin = user.role === "director" || user.role === "executive";
  const tabs = TABS.filter((t) => (t.requiresAdmin ? isAdmin : true));

  return (
    <header className="h-[62px] bg-card border-b border-border flex items-center gap-6 px-6">
      <Link href="/me" className="flex items-center gap-2 font-mono text-[13px] font-semibold tracking-[0.18em]">
        <Database className="w-4 h-4 text-primary" aria-hidden />
        HOLOCRON
      </Link>
      <div className="w-px h-5 bg-border" aria-hidden />
      <nav className="flex items-center gap-1">
        {tabs.map((t) => {
          const active = t.match(pathname);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`px-3 py-2 text-sm relative ${
                active ? "text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label}
              {active && (
                <span className="absolute left-3 right-3 -bottom-[1px] h-[2px] bg-primary" aria-hidden />
              )}
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <ClearanceBadge classification={user.max_clearance} />
        <div className="w-8 h-8 rounded-full bg-accent text-accent-foreground grid place-items-center font-mono text-[11px] font-semibold">
          {initials(user.username)}
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 3: Commit.**

```
git add frontend/components/TopNav.tsx
git commit -m "feat(frontend): add TopNav primitive

Persistent 62px nav bar for authenticated routes. Left: HOLOCRON wordmark
+ Home/Chat/Audit log tabs with active-state underline via usePathname.
Right: ClearanceBadge + initials avatar. Audit-log tab role-gated to
director/executive.

Not yet wired into any route — that lands in Task 10."
```

---

## Task 10: Insert `TopNav` into `/me`, `/chat`, `/admin/audit` and remove redundant nav

**Files:**
- Modify: `frontend/app/me/page.tsx`
- Modify: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/admin/layout.tsx`

**Goal:** Render `TopNav` at the top of each authenticated route. Remove now-redundant nav artifacts: the ad-hoc "Open chat" / "View audit log" buttons on `/me` (from Phase D commit `8e14594` — these become dead code); the inline `<header>` at the top of `/chat` (its role is now owned by `TopNav`). Buttons on `/me` that we keep: **Sign out** stays (page-level CTA, not nav).

- [ ] **Step 1: Update `/me` — insert TopNav, remove nav buttons.**

Open `frontend/app/me/page.tsx`. Add the import:

```tsx
import { TopNav } from '@/components/TopNav';
```

Wrap the `<main>` element with a fragment that renders `TopNav` above it (only after `user` has loaded, not during the loading state):

```tsx
  if (loading) return <main className="p-8">Loading…</main>;
  if (!user) return null;

  return (
    <>
      <TopNav user={{ username: user.username, role: user.role, max_clearance: user.max_clearance }} />
      <main className="mx-auto max-w-2xl p-8 space-y-6">
        ...
      </main>
    </>
  );
```

Then remove the "Open chat" and "View audit log" buttons from the `CardContent` actions row. Keep only "Sign out". The relevant block becomes:

```tsx
          <div className="flex flex-wrap items-center gap-2 pt-2">
            <Button variant="outline" onClick={onLogout}>Sign out</Button>
          </div>
```

- [ ] **Step 2: Update `/chat` — replace inline header with TopNav.**

Open `frontend/app/chat/page.tsx`. Add the import:

```tsx
import { TopNav } from "@/components/TopNav";
```

Delete the entire `<header>...</header>` block currently rendered at the top of the return JSX (the block starting with `<header className="px-4 py-2 border-b border-border flex items-center gap-3 text-sm">`).

Replace it with:

```tsx
      <TopNav user={{ username: me.username, role: me.role, max_clearance: me.max_clearance }} />
```

Note: `me.role` is used by `TopNav`, so verify `role` exists on `MeResponse`. Check the interface at the top of `chat/page.tsx` — the current interface has `role: string`. Good, no addition needed.

- [ ] **Step 3: Update `/admin/audit` — insert TopNav via the admin layout.**

Open `frontend/app/admin/layout.tsx`. Add the import:

```tsx
import { TopNav } from "@/components/TopNav";
```

Change the state to hold the me payload not just `allowed`, then render `TopNav` in the allowed branch. Replace the entire component body with:

```tsx
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<{ username: string; role: string; max_clearance: "public" | "restricted" | "secret" | "top_secret" } | null>(null);
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const meResp = await api.me();
        if (cancelled) return;
        const role = (meResp as { role?: string }).role;
        setMe(meResp as unknown as typeof me);
        if (role === "director" || role === "executive") setAllowed(true);
        else setAllowed(false);
      } catch {
        if (!cancelled) router.push("/login");
      }
    }
    check();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (allowed === null) {
    return <div className="p-8 text-sm text-muted-foreground">Loading admin…</div>;
  }
  if (!allowed) {
    return (
      <div className="p-8 text-sm text-destructive">
        Access denied. Admin views require director or executive role.
      </div>
    );
  }
  return (
    <>
      {me && <TopNav user={{ username: me.username, role: me.role, max_clearance: me.max_clearance }} />}
      <div className="p-8 max-w-6xl mx-auto">{children}</div>
    </>
  );
}
```

Note: the loading and access-denied paths keep the p-8 layout without TopNav (no TopNav for unauthenticated / unauthorized states).

- [ ] **Step 4: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 5: Manual browser walkthrough — the critical check.**

Start `pnpm dev`. Walk this path end-to-end:

1. Visit `/login` (log out first if needed via `/me`'s Sign out). Expected: `/login` renders WITHOUT TopNav. Log in as `manager.hr`.
2. Land on `/me`. Expected: TopNav shows Home (underlined), Chat, no Audit log tab (manager.hr is not director/executive). ClearanceBadge shows RESTRICTED. Avatar shows "MH".
3. Click Chat in TopNav. Expected: navigates to `/chat`, TopNav updates active-tab underline to Chat, prior inline header is gone.
4. Sign out via `/me` Sign out button. Log in as `executive.procurement`.
5. Land on `/me`. Expected: TopNav shows Audit log tab now.
6. Click Audit log. Expected: navigates to `/admin/audit`, TopNav's Audit log underlined, prior page renders below TopNav.
7. Directly URL-visit `/admin/audit` as `manager.hr` (log out, log back in). Expected: access-denied text (no TopNav in denied state — that's intentional).

Stop dev server.

- [ ] **Step 6: Commit.**

```
git add frontend/app/me/page.tsx frontend/app/chat/page.tsx frontend/app/admin/layout.tsx
git commit -m "feat(frontend): wire TopNav into authenticated routes

Renders TopNav on /me, /chat, and /admin/*. Removes the ad-hoc nav
buttons from /me (Open chat / View audit log — shipped in Phase D
commit 8e14594 as a stopgap) since TopNav now owns cross-route nav.
Removes the inline /chat header for the same reason. Sign out stays on
/me as a page-level CTA."
```

---

## Task 11: Mobile breakpoints on all 4 routes

**Files:**
- Modify: `frontend/components/TopNav.tsx`
- Modify: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/admin/audit/page.tsx`
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/me/page.tsx`

**Goal:** Ensure no route breaks at 375px viewport (iPhone SE width). The heavy dashboards land in Pass 2; Pass 1 just adds safe defaults and shims.

- [ ] **Step 1: TopNav — prevent wrap and hide non-essential right-side chrome on small screens.**

In `frontend/components/TopNav.tsx`, tighten the right-side section for small screens. In the outer `<header>`, add `whitespace-nowrap overflow-hidden`. In the right-side flex container, hide the avatar on `<sm`. Update:

Wordmark tightens on `<sm`:
```tsx
      <Link href="/me" className="flex items-center gap-2 font-mono text-[13px] font-semibold tracking-[0.18em] shrink-0">
```

Divider — hide on small:
```tsx
      <div className="hidden sm:block w-px h-5 bg-border" aria-hidden />
```

Right-side wrapper — hide avatar on small:
```tsx
      <div className="ml-auto flex items-center gap-3 shrink-0">
        <ClearanceBadge classification={user.max_clearance} />
        <div className="hidden sm:grid w-8 h-8 rounded-full bg-accent text-accent-foreground place-items-center font-mono text-[11px] font-semibold">
          {initials(user.username)}
        </div>
      </div>
```

Nav tabs — compact padding on small:
```tsx
              className={`px-2 sm:px-3 py-2 text-sm relative ${
```

Outer header — shrink horizontal padding:
```tsx
    <header className="h-[62px] bg-card border-b border-border flex items-center gap-3 sm:gap-6 px-3 sm:px-6 whitespace-nowrap overflow-hidden">
```

- [ ] **Step 2: `/admin/audit` — wrap the table in a horizontal-scroll container.**

In `frontend/app/admin/audit/page.tsx`, wrap the existing `<div className="border border-border rounded-lg overflow-hidden">` around the table with an outer scroll wrapper. Change:

```tsx
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
```

to:

```tsx
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[720px]">
```

And add a matching closing `</div>` after `</table>` — the JSX layout becomes:

```tsx
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[720px]">
            ...unchanged...
          </table>
        </div>
      </div>
```

- [ ] **Step 3: `/chat` — thread padding + empty state.**

In `frontend/app/chat/page.tsx`, the outer `<div className="flex flex-col h-screen">` is fine. Ensure the empty-state container reads mobile-friendly. Change the empty-state's outer div to include responsive horizontal padding:

```tsx
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md text-center w-full">
```

For the assistant messages: verify `MessageAssistant` container class `self-start w-full max-w-[95%]` — that's already mobile-ok. Skip further changes; the heavy chat mobile work lands in Pass 2 when heros redesign.

- [ ] **Step 4: `/login` — reduce vertical padding on small screens.**

Open `frontend/app/login/page.tsx`. The current login page uses a centered card. Ensure the outer container reduces padding on `<sm` and the card fills width up to `max-w-md`. Find the outer container (likely `<main>` or a `<div>` with `min-h-screen`), ensure it has `p-4 sm:p-8` (or similar responsive padding), and the card has `w-full max-w-md`. If the current markup uses fixed padding like `p-8`, change to `p-4 sm:p-8`. If it uses fixed width, add `w-full`. Do not otherwise redesign — Pass 2 handles the split layout.

- [ ] **Step 5: `/me` — verify the identity card is mobile-friendly.**

Open `frontend/app/me/page.tsx`. Change the outer `<main className="mx-auto max-w-2xl p-8 space-y-6">` to `<main className="mx-auto max-w-2xl p-4 sm:p-8 space-y-6">`. Everything inside the Card is already flex-based and stacks naturally.

- [ ] **Step 6: Verify build.**

Run from `frontend/`: `pnpm build`
Expected: PASS.

- [ ] **Step 7: Manual mobile-viewport walkthrough.**

Start `pnpm dev`. Open Chrome/Edge/Firefox DevTools, set responsive mode to iPhone SE (375×667). Walk the routes:

1. `/login` — form card fills width with padding, doesn't overflow.
2. Log in as `executive.procurement`. `/me` — identity card renders full-width, TopNav shows without the avatar on the right (only ClearanceBadge + tabs), Sign out button visible.
3. Click Chat tab in TopNav. `/chat` — TopNav doesn't wrap, tabs stay clickable. Send a message; assistant response fits within the viewport, citation cards stack to 1 column (already responsive from prior grid config).
4. Click Audit log in TopNav. `/admin/audit` — the table container is now horizontally scrollable; you can swipe left/right to see all 6 columns. Filter bar wraps to multiple rows (OK for Pass 1; Pass 2 rebuilds it).

Stop dev server.

- [ ] **Step 8: Commit.**

```
git add frontend/components/TopNav.tsx frontend/app/login/page.tsx frontend/app/me/page.tsx frontend/app/chat/page.tsx frontend/app/admin/audit/page.tsx
git commit -m "feat(frontend): mobile breakpoints for Pass 1 surfaces

- TopNav: hide avatar on <sm, compact tab padding, prevent wrap
- /admin/audit: wrap table in overflow-x-auto with min-w-[720px]
- /login, /me: responsive p-4 sm:p-8 outer padding
- /chat: safe empty-state padding

Heavier per-route mobile design lands in Pass 2's hero components."
```

---

## Task 12: Final Pass 1 verification and CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md`

**Goal:** Run the final gates before merging Pass 1. Update CLAUDE.md so the Phase status accurately reflects Pass 1 shipped, and the "Deferred to Phase E / post-MVP" bucket is renamed to Phase F.

- [ ] **Step 1: Final grep gate.**

Run from `frontend/`:
```
grep -rE "slate-|gray-" app components || echo NONE
```
Expected: `NONE`. If any `gray-` hit remains inside `components/ui/*` (shadcn library files), that's tolerable — those are vendor-owned. Note any exceptions in the commit message.

- [ ] **Step 2: Final `.dark` gate.**

Run from `frontend/`:
```
grep -n "\.dark" app/globals.css || echo NONE
```
Expected: `NONE`.

- [ ] **Step 3: Final radius gate.**

Two greps (basic-grep-safe):

```
grep -rn "rounded-2xl" app components || echo NONE
```
Expected: `NONE` in app code. If shadcn `components/ui/*` has hits, leave them (vendor-owned).

```
grep -rnE "className=\"[^\"]*\\brounded\\b[^-]" app components || echo NONE
```
Expected: `NONE` in app code — every `rounded` should be `rounded-sm`, `rounded-md`, or `rounded-lg`. If a hit shows up, replace per the mapping tables in Tasks 6/7 (bare `rounded` → `rounded-md` for buttons/inputs, `rounded-lg` for cards). If shadcn library files hit, leave them.

- [ ] **Step 4: Emoji gate.**

Run from `frontend/`:
```
grep -rE "🔒|⚠" app components || echo NONE
```
Expected: `NONE`.

- [ ] **Step 5: Final `pnpm build`.**

Run from `frontend/`: `pnpm build`
Expected: PASS. Note the build time and the "Route (app)" table output for reference.

- [ ] **Step 6: Full-route manual walk.**

Start `pnpm dev`. In sequence:

1. `/login` — renders, log in as `employee.security`
2. `/me` — identity card + Sign out only (no ad-hoc nav buttons); TopNav shows Home + Chat; no Audit log tab
3. Click Chat via TopNav → `/chat` — inline header replaced by TopNav; suggested-question buttons in empty state
4. Ask "What's the dress-code policy for off-base events?" — assistant renders with citation grid (accent chips), refusal note with Lock icon
5. Sign out. Log in as `executive.procurement`. `/me` — TopNav now shows Audit log tab
6. `/admin/audit` — page renders with rounded-lg table, expand a row, verify REFUSAL badge = restricted amber, RESPONSE badge = public green
7. Resize to 375px — every route stays usable

Stop dev server.

- [ ] **Step 7: Update CLAUDE.md.**

Open `CLAUDE.md`. Under the `## Phase status` heading, add a new bullet AFTER the Phase D line:

```markdown
- **Phase E — Frontend Revamp:** 🟡 **Pass 1 (Foundation) merged.** Design tokens seeded from the local (gitignored) design handoff; every `slate-*`/`gray-*` utility migrated to semantic tokens; two emoji swapped for lucide icons; `TopNav` primitive lands on all authenticated routes; `ClearanceBadge` + `CitationChip` polished; mobile breakpoints on all 4 routes; `.dark` block deleted (dark mode out of scope for Phase E). Pass 2 (Hero components: `/login` demo picker, `/me` dashboard, `CitationCard`/`ConflictCard`/`RefusalNote`/empty-state redesigns, `/admin/audit` summary + data-table, two additive backend endpoints) pending in a later session. See [spec](docs/superpowers/specs/2026-07-01-phase-e-frontend-revamp-design.md) · [Pass 1 plan](docs/superpowers/plans/2026-07-01-phase-e-pass-1-foundation.md).
```

Then find the heading `### Deferred to Phase E / post-MVP` and rename it to `### Deferred to Phase F / post-MVP`. Content inside stays exactly the same.

- [ ] **Step 8: Commit.**

```
git add CLAUDE.md
git commit -m "docs(claude.md): mark Phase E Pass 1 shipped; rename deferred bucket to Phase F

Phase E section added under Phase status (Pass 1 done, Pass 2 pending).
The 'Deferred to Phase E / post-MVP' bucket is renamed to 'Deferred to
Phase F / post-MVP' to free the Phase E label for the frontend revamp."
```

- [ ] **Step 9: Merge decision point.**

You are on the `phase-e` branch with all Pass 1 commits. Options:

**A. Merge to main now (recommended if Pass 2 will be a separate branch cut):**
```
git checkout main
git merge --ff-only phase-e
git push origin main
git checkout -b phase-e-pass-2      # optional; or reuse phase-e
```

**B. Keep on `phase-e` and land Pass 2 in the same branch, then squash-merge later:**
No commands needed — continue with Pass 2 on this branch when it lands.

**C. Open a PR** for review before merge:
```
git push -u origin phase-e
gh pr create --title "Phase E Pass 1: Frontend foundation revamp" --body "..."
```

Merge decision is out of scope for this plan — record it in the next session's handoff. If you're solo-driving and confident, A is clean and matches the Phase D pattern.

---

## Summary of shipped artifacts (Pass 1)

**Created:**
- `frontend/components/TopNav.tsx`
- `frontend/components/CitationChip.tsx`

**Modified:**
- `frontend/app/globals.css` (tokens + delete `.dark`)
- `frontend/tailwind.config.ts` (expose tokens)
- `frontend/lib/clearance-color.ts` (semantic tokens + dot classes helper)
- `frontend/components/ClearanceBadge.tsx` (mono + dot pattern)
- `frontend/app/login/page.tsx` (semantic tokens + mobile padding)
- `frontend/app/me/page.tsx` (semantic tokens + TopNav + remove ad-hoc nav)
- `frontend/app/chat/page.tsx` (semantic tokens + TopNav replaces inline header)
- `frontend/app/chat/components/*.tsx` (all 7 components migrated + emoji → icons)
- `frontend/app/admin/layout.tsx` (semantic tokens + TopNav)
- `frontend/app/admin/audit/page.tsx` (semantic tokens + horizontal-scroll shim)
- `frontend/app/admin/audit/components/*.tsx` (semantic tokens + event badges)
- `CLAUDE.md` (Phase status + Phase F rename)

**Not modified in Pass 1** (Pass 2 territory):
- `/login` layout — still single card, split layout is Pass 2
- `/me` — no Recent queries, no DemoQuestions yet
- Hero components (`CitationCard`, `ConflictCard`, `RefusalNote`) — visually migrated but structurally unchanged; hero rewrites are Pass 2
- `/admin/audit` — no summary stats, no data-table primitive, no chip filter bar yet
- Backend — no new endpoints (those land in Pass 2)
