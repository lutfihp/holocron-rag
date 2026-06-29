---
name: HOLOCRON Phase B — Ingestion + Classification-Aware Retrieval
status: Approved (design)
date: 2026-06-27
owner: Lutfi
parent_spec: 2026-06-27-holocron-design.md
phase: B
budget: ~25–30 hrs
---

# Phase B — Ingestion + Classification-Aware Retrieval

This document refines spec §10.2 with the concrete execution decisions made during brainstorming. The parent spec (`2026-06-27-holocron-design.md`) remains the source of truth for product vision, data model, and overall phasing. Phase B implements the first flagship capability — **clearance-aware hybrid retrieval with honest refusal** — and the synthetic corpus that backs it.

## Locked decisions

These four decisions deviate from or refine the parent spec; they are binding for Phase B.

| # | Decision | Rationale |
|---|---|---|
| 1 | **Corpus is co-authored.** Claude drafts a 4-doc starter set for voice calibration; user edits tone; remaining ~12 docs are batched off the established voice. | Keeps voice authentic to user's enterprise-corporate framing without burning the full 6–8 hr corpus-writing budget on solo authoring. |
| 2 | **Groq `llama-3.3-70b-versatile` replaces Gemini Flash as the LLM.** Embedding provider is separate. | Free API tier with no credit-card friction. Groq is inference-only — does not offer embeddings. |
| 3 | **Embeddings via local `BAAI/bge-base-en-v1.5` (768-dim, sentence-transformers).** Replaces Gemini `text-embedding-004`. Schema `VECTOR(768)` is preserved. | No API rate limits, fully offline, deterministic, retrieval-tuned. Quality difference vs. Gemini is marginal (~1–2 pp on MTEB retrieval) and further mitigated by hybrid search. |
| 4 | **Light audit writes land in Phase B.** A minimal `AuditRepository` writes `query` and `refusal` event rows directly from the retrieval endpoint. Full `services/audit/` event taxonomy and viewer still ship in Phase D. | Refusal reference IDs are meaningless unless persisted with their `withheld_ids`. ~30 min of code in Phase B earns the demo its credibility. |

## Module layout

New code under `backend/app/` (existing Phase A modules unchanged):

```
domain/
  chunk.py                  # Chunk, ChunkWithDocument, RetrievalResult, RefusalContext
  document.py               # Document, DocumentFrontmatter
repositories/
  document_repository.py    # tenant-scoped CRUD on documents
  chunk_repository.py       # ★ unconditional ClearanceContext on every read
  audit_repository.py       # ★ minimal: insert_query / insert_refusal (Phase B scope only)
services/
  ingestion/
    __init__.py             # public API: ingest_corpus_dir(path, tenant_id) → IngestionReport
    loader.py               # SimpleDirectoryReader + frontmatter parser
    splitter.py             # SemanticSplitterNodeParser w/ SentenceSplitter fallback
    embedding.py            # EmbeddingProvider Protocol + BgeEmbeddingProvider impl
    pipeline.py             # orchestrates loader → splitter → embedder → repo persist
  retrieval/
    __init__.py             # public API: search(query, ctx, tenant_id) → SearchResponse
    bm25.py                 # tsvector query builder + execution
    vector.py               # pgvector query builder + execution
    rrf.py                  # reciprocal rank fusion (pure function)
    refusal.py              # parallel unfiltered count + ref-id generation + audit insert
api/
  retrieval.py              # POST /retrieval/search router
core/
  clearance.py              # ClearanceContext value object (frozen dataclass)
scripts/
  seed_corpus.py            # idempotent re-ingest CLI
corpus/                     # NEW top-level dir; markdown docs with frontmatter
```

**Boundary rules (enforced by types where possible):**

- `ChunkRepository` read methods all require a `ClearanceContext` parameter. There is no `get_all_chunks()` — only `search_chunks(ctx, ...)`. RBAC bypass becomes a type error, not a runtime risk.
- `EmbeddingProvider` is a `Protocol`. The real `BgeEmbeddingProvider` and the test `FakeEmbeddingProvider` are interchangeable via DI — no `if test:` branches in production code.
- `seed_corpus.py` is idempotent by deleting all `documents WHERE tenant_id=? AND source_uri LIKE 'corpus/%'` before re-inserting. `ON DELETE CASCADE` on chunks handles the rest.

## Ingestion pipeline

```
corpus/**/*.md
   │
   ▼
SimpleDirectoryReader  ──► raw Document objects (text + filepath)
   │
   ▼
frontmatter parser     ──► (text_body, DocumentFrontmatter)
   │                       fails loud on missing/invalid frontmatter, citing file path
   ▼
DocumentRepository.insert(...)  ──► documents.id
   │
   ▼
SemanticSplitterNodeParser  ──► List[LlamaIndex Node]
   │                              fallback to SentenceSplitter(chunk_size=512, overlap=50)
   ▼
BgeEmbeddingProvider.embed_batch(texts, batch=32)  ──► List[np.ndarray[768]]
   │
   ▼
ChunkRepository.bulk_insert([Chunk(...)])
```

**Frontmatter contract:**

```yaml
---
title: Death Star Reactor Operations Manual
classification: restricted          # public|restricted|secret|top_secret
department: engineering
version: "2.3"
effective_date: 2023-08-01
lineage_id: reactor-manual          # free-form slug; groups versions of "same" doc
---
```

**Out of scope for Phase B:** `chunks.entities` stays default `'{}'`. Entity extraction lands in Phase C alongside conflict detection.

**Batching:** BGE handles ~32 chunks/forward pass on CPU. Total corpus (~300–500 chunks) embeds in under a minute on a developer machine.

## Retrieval pipeline

### Endpoint

`POST /retrieval/search` — authed via the existing `holocron_session` cookie; tenant + user resolved by the same dependency used in `/auth/me`.

Request:
```json
{ "query": "What's the dress-code policy for off-base events?", "top_k": 6 }
```

Response:
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_title": "Imperial Employee Handbook",
      "classification": "public",
      "department": "hr",
      "effective_date": "2019-04-12",
      "snippet": "...off-duty conduct shall...",
      "score": 0.0312,
      "rank": 1
    }
  ],
  "refusal": {
    "withheld_count": 2,
    "reference_id": "A7F2-CXJK"
  }
}
```

`refusal` is `null` when nothing was withheld.

### Flow

```
1. ClearanceContext = (max_clearance, departments) from authed user
2. Embed query  ──► query_vec (768-d, BGE; same model as ingest)
3. asyncio.gather:
     a. bm25_topn(query, ctx, n=25)        ──► [(chunk_id, bm25_rank)]
     b. vector_topn(query_vec, ctx, n=25)  ──► [(chunk_id, vec_rank)]
     c. unfiltered_topn_ids(query, query_vec, n=25)
        ──► set of chunk_ids that would appear in top-25 ignoring RBAC
4. rrf_fuse(bm25, vector, k=60) ──► top top_k chunks
5. filtered_ids = set of chunk_ids returned by (a ∪ b)
   unfiltered_ids = set from (c)
   withheld_count = |unfiltered_ids - filtered_ids|
6. if withheld_count > 0:
       ref_id = gen_ref_id()
       AuditRepository.insert_refusal(tenant_id, user_id, ref_id,
                                      retrieved_ids=filtered_ids,
                                      withheld_ids=unfiltered_ids - filtered_ids)
   else:
       ref_id = null
7. AuditRepository.insert_query(tenant_id, user_id, query_text, retrieved_ids)
8. Return SearchResponse
```

### RBAC SQL filter

Lives in `chunk_repository.py`; applied to both BM25 and vector queries.

```sql
WHERE tenant_id = :tenant
  AND classification = ANY(:allowed_levels)
  AND (department = ANY(:departments) OR classification = 'public')
```

`allowed_levels` is computed Python-side from a constant `CLEARANCE_RANK = {public: 0, restricted: 1, secret: 2, top_secret: 3}`. Chosen over a `CASE`-expression approach because the mapping is unit-testable in isolation and the SQL stays simple.

### Refusal counting semantics

Refusal counting compares the **union of top-25 BM25 + top-25 vector** IDs with and without RBAC. This makes "N higher-clearance sources may be relevant" mean "N chunks that *would have shown up in your retrieval* were withheld" — not "N total higher-clearance chunks exist in the system." The former is informative; the latter would be alarming and uselessly large.

### Reference ID format

`[A-Z2-7]{4}-[A-Z2-7]{4}` — base32, ~40 bits entropy. Generated per refusal. Persisted to `audit_events.refusal_ref` alongside `withheld_ids`. No uniqueness constraint — collision risk is irrelevant for the demo, and traceability comes from the persisted `withheld_ids`.

### Error handling

| Condition | Response |
|---|---|
| Empty query | 422 |
| Unauthenticated | 401 |
| BGE model load failure | 503 with `Retry-After` header |
| Zero results, zero withheld | 200 with empty `results` and `refusal: null` |

## Synthetic corpus

### Round 1 — voice calibration (4 starter docs)

Claude drafts; user edits tone. These four cover both demo paths in parent spec §1:

| # | File | Classification | Department | Purpose |
|---|---|---|---|---|
| 1 | `corpus/hr/employee_handbook_2019.md` | public | hr | Demo A — base policy |
| 2 | `corpus/hr/management_conduct_supplement_2023.md` | restricted | hr | Demo A — conflicting supplement |
| 3 | `corpus/engineering/reactor_operations_manual_2019.md` | restricted | engineering | Demo B — base manual |
| 4 | `corpus/engineering/reactor_operations_manual_2023.md` | restricted | engineering | Demo B — amendment with conflict |

### Round 2 — batched fill-in (~12 docs)

Generated in three directory-grouped batches once voice is locked. Required coverage from parent spec §6:

| Coverage requirement | Documents |
|---|---|
| ≥3 lineage pairs | Demo A pair, Demo B pair, +1 procurement pair (`procurement_policy_2020` / `_2024`) |
| ≥4 classification ladders | dress-code (public→restricted), recruitment (public→restricted→secret), reactor (restricted→secret), executive search (secret→top_secret) |
| ≥2 cross-department conflicts | engineering/safety_threshold vs fleet_ops/deployment_threshold; security/access_audit_freq vs hr/onboarding_audit_freq |
| ≥1 outdated-but-not-superseded | `hr/remote_work_policy_2018.md` |

**Final distribution (~16 docs):** `hr/` ×4, `engineering/` ×4, `fleet_ops/` ×3, `security/` ×3, `procurement/` ×2.

### Voice guardrails

Enterprise-corporate tone, not Star Wars-pastiche. Documents read like real internal policies: section headers, bullet lists, "Approved by" footers, effective dates, revision history blocks. The Imperial flavor lives in proper nouns (Death Star, Coruscant, Stardate references) and in occasional in-character names of approvers. **Not** in dramatic prose.

### Document parameters

- Length: 600–1500 words per doc → 10–30 chunks per doc → ~300–500 chunks total.
- Conflict seeding is **mechanical, not subtle.** Directly opposing numeric or procedural claims (e.g., "shutdown sequence: A→B→C" vs "C→B→A"). Subtle conflicts make for bad demos and bad eval signal.

## Testing strategy

| Layer | What's tested | How |
|---|---|---|
| Unit (no DB) | `rrf.py` fusion math; `refusal.py` ref-id generator; `splitter.py` chunk-boundary edges; `loader.py` frontmatter parser (valid/missing/bad-type); `CLEARANCE_RANK` mapping | Pure pytest, no fixtures |
| Repository (DB, no embeddings) | `ChunkRepository` RBAC filter across 4 clearances × 5 departments; `DocumentRepository` tenant scoping; `AuditRepository` insert+read | Per-test DB fixture (existing Phase A pattern); fake chunks inserted via SQL with fixed vectors |
| Service-level (DB + fake embeddings) | Full `ingestion.pipeline` end-to-end on 3-doc test corpus using `FakeEmbeddingProvider`; full `retrieval.search` against seeded fake-vector corpus; RRF ranking with controlled inputs; refusal counting across clearance tiers | `EmbeddingProvider` injected as fake; existing per-test DB fixture |
| API (FastAPI TestClient) | `POST /retrieval/search` happy path per clearance tier; 401 unauth; 422 empty query; refusal block populated when `withheld_count > 0`; audit row written | Existing auth-cookie test pattern |
| Manual smoke (not in `pytest`) | `python scripts/seed_corpus.py` against real corpus + real BGE model; spot-check 3 demo queries via curl | Documented as a task; run before declaring phase done |

### `FakeEmbeddingProvider`

Single seam that keeps every automated test fast and deterministic:

```python
class FakeEmbeddingProvider:
    """Hash-based 768-d vectors. Same text → same vector; close texts → close vectors."""
    def embed_one(self, text: str) -> np.ndarray: ...
    def embed_batch(self, texts: list[str]) -> list[np.ndarray]: ...
```

"Close texts → close vectors" is achieved by hashing overlapping n-grams into bucket indices and incrementing those positions. Not a real semantic embedding, but enough for vector-search tests to exhibit "similar query retrieves similar chunk" behavior deterministically.

### Targets

- **~50–70 new tests** (suite: 30 → ~85–100).
- Total run time **under 15 seconds.**

## Exit criteria (end-of-phase demo)

1. `python scripts/seed_corpus.py` ingests the full corpus in under 60 seconds; idempotent on re-run.
2. `curl -X POST /retrieval/search` (cookie from `executive.fleet`) for *"What's the dress code policy for off-base events?"* returns ≥1 result from the public Employee Handbook AND ≥1 from the restricted Management Conduct Supplement.
3. Same query as `employee.security` returns only the public Employee Handbook AND `refusal: {withheld_count: ≥1, reference_id: "XXXX-XXXX"}`.
4. `SELECT * FROM audit_events WHERE refusal_ref IS NOT NULL` shows the refusal row with `withheld_ids` populated — the ref ID is verifiable.
5. Same query as `director.engineering` (no HR dept) returns zero HR results AND non-zero withheld count.
6. Cross-department query (Demo B: reactor shutdown) returns engineering chunks for engineering users only.
7. All ~85–100 tests green; suite under 15 s.
8. README updated with `make seed-corpus` and a sample curl flow.

## Known follow-ups deferred to later phases

- `services/audit/` full event taxonomy + structlog wiring → Phase D.
- `/admin/audit` viewer UI → Phase D.
- `chunks.entities` population + conflict detection → Phase C.
- `services/answer_generation/` + `POST /chat/ask` → Phase C.
- Frontend `/chat` and `/admin/documents` pages → Phase C.
- arq + Redis re-embed worker → out of MVP scope.
