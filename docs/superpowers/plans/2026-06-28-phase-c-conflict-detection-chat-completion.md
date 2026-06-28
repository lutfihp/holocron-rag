# Phase C — Conflict Detection + Chat Frontend: Completion Record

Date verified: 2026-06-28 (code complete; manual browser walkthrough pending user verification)
Branch: main

## End-of-phase demo checklist (from spec §7.1)

> Code path is fully wired and tested. Final manual browser walkthrough is still pending — the user needs to run `pnpm dev` + `uvicorn` and walk each demo path. Items below describe the implementation state, not browser-verification status.

- [ ] `pnpm dev` + `uvicorn` running; navigate to `/chat`. — **Page implemented at `frontend/app/chat/page.tsx` with auth gate, empty state, error handling. User to verify in browser.**
- [ ] Demo A — executive view (executive.procurement, dress-code question). — **Backend wiring exists end-to-end (retrieval → conflict detection → answer generation → audit). User to verify in browser.**
- [ ] Demo A — employee view (employee.security, same question). — **Refusal path implemented and surfaces in `ChatResponse.refusal`. User to verify in browser.**
- [ ] Demo B — director view (director.engineering, reactor coolant). — **Lineage-pair conflict path covered by prefilter. User to verify in browser.**
- [ ] Demo B — employee view (employee.security, same question). — **Refusal path implemented. User to verify in browser.**
- [ ] Inline `[n]` chips scroll to citation card on click. — **Implemented via hash anchors (`#cite-{marker}`) in `CitationCard` and `MessageAssistant`. User to verify in browser.**
- [x] All Phase A + B + C tests pass; suite under ~30s default. — **131 passed, 3 deselected in 32.69s (see Step 1 actuals below).**
- [ ] `audit_events` rows for `query`, `response`, (where applicable) `refusal`. — **`AuditRepository.insert_query`, `.insert_response`, `.insert_refusal` all wired in `/chat/ask`. User to verify via psql after demo run.**

## Test results

- Default suite: **131 passed, 3 deselected** in ~32.7 seconds.
- Slow suite (`-m slow`): 4 passed (2 BGE Phase B + 2 spaCy real). No real-Groq slow test was added in Phase C (deferred — fakes cover the deterministic path; live Groq behavior is exercised via the manual demo).

## Notable plan deviations (and why)

1. **`llama-index-llms-groq>=0.3,<0.4`** instead of spec's `>=0.2,<0.3` — version 0.2.x requires `llama-index-core<0.12` which conflicts with Phase B's lock at `>=0.12,<0.13`. Verified by inspecting wheel METADATA. Plan/spec should be updated.
2. **spaCy `_load_spacy()` does NOT pass `disable=["parser","lemmatizer"]`** — the plan called for that, but parser is required for `doc.noun_chunks` (raises E029) and lemmatizer is required for `token.lemma_` to return non-empty strings. The plan's Step 5 slow test specifically anticipated this risk. Full default pipeline is loaded.
3. **`GroqLLMClient._sleep` await call uses `inspect.isawaitable` shim** — the plan's reference test monkeypatches `_sleep` to a sync lambda but the plan's reference implementation uses `await self._sleep(...)`. The shim reconciles both. Worth simplifying in Phase D.
4. **Wasted final-attempt sleep fix (commit `2f1429f`)** — the plan's retry loop slept after the final fallback attempt and then immediately raised, costing 2s of tail latency. Loop now skips sleep on the absolute last attempt.
5. **`RetrievalResult` / `ChunkHit` / `ChunkRepository` extended with `lineage_id` + `entities` columns** — done as part of Task 5 (prefilter) because the prefilter needs both. SELECT positions shifted (score now at row[9]). Phase D should migrate to `.mappings()`.
6. **Task 13 test added `seeded_chunk` fixture** — the plan's `test_chat_ask_returns_full_payload` asserted on LLM-scripted text but with no seeded chunks `generate_answer` short-circuits to the fallback string. Seeded one public chunk.
7. **Task 15 renamed Phase A `ClearanceBadge` prop** from `level` to `classification` and updated the one Phase A consumer (`frontend/app/me/page.tsx`). Pragmatic — the two types are structurally identical.

## Spec coverage

- §1.3 locked decisions (all 13): implemented as written modulo the version/disable deviations above.
- §2 module layout: implemented; `services/conflict_detection/` and `services/answer_generation/` packages match plan.
- §3 conflict-detection pipeline: full — entity extraction at ingest, prefilter thresholds (lineage / same-dept ≥2 / cross-dept ≥3 / cap 4), judge with orderless cache and `LLMUnavailable` resilience, parallel `asyncio.gather` orchestrator.
- §4 answer generation: full — `CompactAndRefine`-pattern prompt templates, citation parser with out-of-range filter, `generate_answer` service with conflict-marker reassignment and empty-chunks fallback.
- §5 API contract: full — `POST /chat/ask` returns 200/400/401/503; audit writes `query` + `response` (+ `refusal` when applicable) per request.
- §6 frontend: full — `/chat` page with auth gate, suggested empty state, error retry, in-page thread, inline citation chips that hash-link to citation cards.
- §7 exit criteria: code-complete; manual demo walkthrough pending user verification.

## Known follow-ups for Phase D

- `/admin/documents` upload + list page
- `/admin/audit` viewer
- Disk cache for Groq responses (eval-driven)
- structlog → JSON stdout
- Evaluation harness + `golden_set.yaml` + `make eval`
- arq + Redis re-embed worker
- Streaming responses
- Migrate `ChunkRepository` SELECT row reads to `.mappings()` (named column access)
- Simplify `GroqLLMClient._sleep` shim (drop `inspect.isawaitable`)
- Add a real-Groq slow test (`@pytest.mark.slow`) for `/chat/ask` end-to-end
- Fix pre-existing `frontend/app/layout.tsx` Geist font import error from Phase A
- Update `pyproject.toml` deps to match reality (`llama-index-llms-groq>=0.3,<0.4`)
- Update spec/plan documents to reflect actual deviations enumerated above
- Consider warming BGE + spaCy + Groq client at startup so first `/chat/ask` is not 60s
