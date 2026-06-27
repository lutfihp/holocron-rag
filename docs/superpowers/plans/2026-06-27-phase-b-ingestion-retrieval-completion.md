# Phase B — Ingestion + Classification-Aware Retrieval: Completion Record

Date verified: 2026-06-27
Branch: `phase-b` (23 commits from `main`)

## End-of-phase demo checklist

All criteria from [the spec exit checklist](../specs/2026-06-27-phase-b-ingestion-retrieval.md#exit-criteria-end-of-phase-demo):

- [x] `python scripts/seed_corpus.py` ingests the full corpus (18 documents → 39 chunks). First-run total time 128s including BGE model load; pure ingest after model cache hit is ~30s. Idempotent on re-run (delete-by-source-prefix + re-insert).
- [x] **Demo A path verified.** `executive.procurement` (departments `[procurement, hr]`) searching "dress code policy off-base events" returns 6 results: 3 public *Imperial Employee Handbook* chunks + 2 restricted *Management Conduct Supplement* chunks + 1 *Manager Tier Hiring Guidelines* chunk. `refusal: null` not asserted here because exec.proc still has 6 withheld chunks (from non-HR depts they can't see); the spec exit criterion was about *the two specific documents*, both of which appeared.
- [x] **Refusal flow verified.** `employee.security` (public clearance, security dept) searching the same query returns ONLY public chunks; refusal block populated: `{withheld_count: 13, reference_id: "MGMO-C65Q"}`.
- [x] **Audit row verified.** `SELECT * FROM audit_events WHERE refusal_ref IS NOT NULL` returns 5 refusal rows across the smoke session, each with populated `withheld_ids` arrays. The ref ID returned to the client is the same value persisted in `refusal_ref`.
- [x] **Department filter verified.** `director.engineering` (no HR department) searching the dress-code query returns zero HR results; `executive.fleet` (no HR department) also returns zero HR-restricted results — both consistent with the RBAC SQL filter (`department = ANY(:depts) OR classification = 'public'`).
- [x] **Cross-department reactor query verified.** `director.engineering` searching "reactor shutdown sequence" returns 4 chunks from the two Reactor Operations Manual versions; `employee.security` searching the same query returns zero engineering chunks (all 6 results were public HR/IT). Lineage pair retrieval works as designed.
- [x] **All ~88 tests green, suite under 25s** (`-m 'not slow'` default). Final count: 88 passing, 2 deselected (the opt-in BGE slow tests).
- [x] README updated with `make seed-corpus`, sample retrieval query (PowerShell), and a first-call BGE latency note.

## Notable plan deviations (and why)

1. **`services/retrieval/{bm25,vector}.py` collapsed into `ChunkRepository` methods.** The design spec listed BM25 and vector lookup as separate submodules under `services/retrieval/`. In execution, those submodules would have been one-method passthroughs to the repository — repositories own SQL, so SQL belongs there. Final layout: `ChunkRepository.bm25_topn`, `vector_topn`, `unfiltered_topn_ids`; `services/retrieval/` keeps `rrf.py` (pure function), `refusal.py` (ref-id + audit), and `__init__.py::search` (orchestration). Documented in the plan up front.

2. **SemanticSplitter → SentenceSplitter only.** Spec called for `SemanticSplitterNodeParser` with `SentenceSplitter` fallback. Executed with `SentenceSplitter` only in Phase B. Reasoning: semantic splitting requires running BGE during ingest, multiplies embed calls 2–3×, and the quality lift on enterprise-policy prose is marginal. Phase C can swap if eval signal demands it. Documented in the plan up front.

3. **Corpus expanded from planned 16 to actual 18 documents** following mid-execution user request for "less engineering document and more on HR and common departments, add IT too." Revised distribution: HR ×7, IT ×3, Security ×3, Engineering ×2, Procurement ×2, Fleet Ops ×1 = 18. Within spec §6 range ("~15–20 markdown documents"). Required adding `Department.IT = "it"` to [enums.py](../../../backend/app/domain/enums.py) and updating `test_departments_listed`.

4. **`Chunk` Python attribute renamed `text` → `text_`** to avoid shadowing the imported `sqlalchemy.text` function in the class body. Column name in SQL remains `text` via the `mapped_column("text", ...)` override. The trailing underscore is the only place this name leaks; all repo code and tests use `text_=...` consistently.

5. **conftest `db_session` fixture now pre-creates `vector` and `pgcrypto` extensions** before `Base.metadata.create_all`. The Phase A migration creates these via Alembic, but the test fixture uses `create_all` directly and doesn't run migrations. Without the explicit `CREATE EXTENSION IF NOT EXISTS vector`, every Phase B chunk test would fail to create the `VECTOR(768)` column.

6. **`pytest -m 'not slow'` default.** Two BGE tests are real-model tests that download ~440 MB and take ~2 minutes. They live in `tests/test_embedding_bge.py` marked `@pytest.mark.slow` and are deselected by default. Opt-in run: `pytest -m slow`.

7. **`text_tsv` column shared via raw SQL, not the ORM.** SQLAlchemy can model `TSVECTOR GENERATED ALWAYS AS (...) STORED` via `Computed(persisted=True)`, which is what `models.py` does. But the `bm25_topn` query uses raw SQL via `sql_text(...)` because the `plainto_tsquery` + `ts_rank` combo is cleaner expressed inline than via SQLAlchemy expressions. Same for the vector queries (`<=>` operator + `CAST(... AS vector)` literal).

8. **One pre-existing Phase A test flaked once** during the run (`test_tampered_token_rejected`). It passed on immediate re-run and remained green for the rest of the phase. The test tampers with a JWT signature by random byte mutation, which has a non-zero probability of producing a valid signature by accident; the test should be hardened in Phase D when we touch security tests. Not a Phase B regression.

## Spec coverage

- §1 (locked decisions, all four): implemented as written.
- §2 (module layout): implemented with the `bm25/vector → ChunkRepository` refinement noted above.
- §3 (ingestion pipeline): full — loader, splitter, embedder Protocol, BGE provider, pipeline orchestration, idempotent seed CLI.
- §4 (retrieval pipeline): full — RBAC SQL filter in repository, RRF fusion, parallel unfiltered count, refusal ref-id generation and audit persistence.
- §5 (synthetic corpus): 18 documents (vs planned 16) covering all four required coverage categories — 3 lineage pairs (employee-handbook, reactor-manual, procurement-policy), 4 classification ladders (dress-code, recruitment, IT-access, executive-search), 2 cross-department conflicts (HR/Security audit cadence, IT/Security incident response), 1 outdated doc (remote_work_2018).
- §6 (testing strategy): full — unit, repository, service, API layers; `FakeEmbeddingProvider` seam; opt-in BGE slow tests; 88 total tests under 25s.
- §7 (exit criteria): all 8 verified end-to-end in smoke test.

## Known follow-ups for Phase C

- **Entity extraction at ingest time** — `chunks.entities` is currently always `[]`. Phase C populates it with a lightweight NER pass, feeding the heuristic prefilter for conflict detection.
- **Conflict detection service** — heuristic prefilter (lineage-pair + same-department-overlapping-entities) → Groq `llama-3.3-70b-versatile` as judge → in-memory LRU cache.
- **Answer generation** — LlamaIndex `Refine`/`CompactAndRefine` synthesizer with inline `[1]`, `[2]` citation markers and conflict-acknowledging prose.
- **`POST /chat/ask`** orchestrating retrieval → conflict detection → answer generation.
- **Frontend `/chat` and `/admin/documents`** pages.
- **Lower default `chunk_size`** if eval shows we want more granular retrieval. Current 512-token default yields ~2 chunks per ~1000-word document; the spec estimate was 300–500 total chunks (we have 39). Demos work, but Phase D eval will tell.
- **Backend without `--reload` does not auto-reload on code changes.** Worth noting in the dev docs since I hit this during smoke — a long-running uvicorn process was responding with stale routes.
- **First `/retrieval/search` call after a fresh `uvicorn` process** takes 60+ s due to lazy BGE model load via the `lru_cache` singleton. Acceptable for now; Phase D could warm the model at startup if eval runs feel sluggish.
