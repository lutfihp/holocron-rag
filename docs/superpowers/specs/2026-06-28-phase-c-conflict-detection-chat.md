---
name: HOLOCRON Phase C — Conflict Detection + Chat Frontend
status: Approved (design)
date: 2026-06-28
owner: Lutfi
parent_spec: 2026-06-27-holocron-design.md
phase: C
---

# Phase C — Conflict Detection + Chat Frontend

This spec covers the third of four MVP phases. Phase A delivered the auth/RBAC foundation; Phase B delivered ingestion and classification-aware hybrid retrieval. Phase C delivers the second flagship capability — **automatic knowledge-conflict detection** — together with the **`/chat` frontend** that makes both flagship demos reproducible end-to-end in the browser.

The exit criterion for Phase C is that both headline demos from the design spec §1 work in the browser without any code changes.

---

## 1. Scope and locked decisions

### 1.1 In scope (5 deliverables)

1. **Entity extraction at ingest time.** spaCy `en_core_web_sm` extracts named entities + lemmatised noun chunks. Populates `chunks.entities` so the heuristic conflict prefilter can fire on cross-document, cross-department overlaps.
2. **`services/conflict_detection/`.** Heuristic prefilter over top-k=6 chunks → Groq LLM-as-judge per candidate pair → in-process LRU keyed on chunk-pair → list of `Conflict` value objects.
3. **`services/answer_generation/`.** LlamaIndex `CompactAndRefine` synthesizer with a fully custom prompt template that produces inline `[1]`, `[2]` citation markers and conflict-acknowledging prose when conflicts are present.
4. **`POST /chat/ask`** endpoint orchestrating retrieval → conflict detection → answer generation; returns the full assistant turn payload.
5. **Frontend `/chat`.** In-page chat thread (React state only, no DB persistence) with user bubbles, assistant messages, citation cards, conflict cards, refusal blocks, and inline citation chips that scroll to matching cards.

### 1.2 Deliberately out of scope (deferred to Phase D)

- `/admin/documents` upload form and document list page.
- `/admin/audit` viewer.
- Disk-backed response cache for Groq.
- structlog → JSON stdout configuration.
- Evaluation harness, `golden_set.yaml`, `make eval`.
- arq + Redis re-embed worker.
- Streaming responses.

### 1.3 Locked architectural decisions

| # | Decision | Choice | Reason |
|---|---|---|---|
| 1 | Entity extractor | spaCy `en_core_web_sm`. Both NER spans and `noun_chunks`, lemma-lowercased, deduplicated. | Catches cross-department topic overlap (e.g. "audit cadence", "incident response") that pure NER would miss. |
| 2 | Conflict cache key | `tuple(sorted([chunk_id_a, chunk_id_b]))`. | A conflict is a property of the chunk pair, not the query that retrieved them. Maximises reuse across queries. |
| 3 | Conflict cache impl | `functools.lru_cache(maxsize=256)` wrapping the LLM judge call only. Module-global, lost on process restart. | No Redis needed in Phase C. 256 entries comfortably exceeds expected unique judged pairs over the corpus. |
| 4 | Prefilter pair cap | Max 4 pairs sent to the judge per query. Pairs ranked by ascending `a.rank + b.rank` (lower = better). | Bounds LLM cost. Corpus typically yields 1–2 pairs after prefilter; 4 is the safety belt. |
| 5 | Answer synthesizer | LlamaIndex `CompactAndRefine` with a custom `text_qa_template` and `refine_template`. | Matches the design spec §10.3. Familiar canonical RAG stack. Refine template only fires if a future chunk-size increase pushes context past one batch. |

> **Phase D amendment (2026-06-28):** Phase C shipped a *pattern-only* implementation
> (compact context block + single LLM call) without instantiating the LlamaIndex
> synthesizer object. Phase D Task 2 replaces this with a real `CompactAndRefine`
> synthesizer driven through a thin `HolocronGroqLLM` adapter that forwards calls
> to `GroqLLMClient.complete_text`. Retry/fallback policy remains in
> `GroqLLMClient`; the adapter is wire-only.

| 6 | Groq primary model | `llama-3.3-70b-versatile`. | Already configured in environment via `GROQ_API_KEY`. Strong quality for both judge and synthesis. |
| 7 | Groq fallback model | `llama-3.1-8b-instant` on persistent rate-limit. | More lenient rate limits; smaller but acceptable for both call paths. |
| 8 | Retry ladder | 3 attempts on primary (backoff 0.5s → 1s → 2s), then 3 attempts on fallback (same backoff). Six total before raising `LLMUnavailable`. | Robust enough for live demos without disk caching. |
| 9 | Conflict-judge failure | Silent: judge returns `None`; conflict service excludes the pair; response carries an empty `conflicts: []` array. | Low criticality — demo continues with degraded conflict surfacing. |
| 10 | Answer-gen failure | Surface HTTP 503 with `{"detail": "LLM temporarily unavailable. Please retry."}`. UI shows retry banner. | High criticality — user must know rather than receive a blank or hallucinated answer. |
| 11 | Chat UI idiom | In-page chat thread. React `useState<Turn[]>` only; no DB, no localStorage, no URL state. Page reload clears. | Modern AI-product look without taking on storage scope. Matches design-spec non-goals. |
| 12 | Assistant message block order | (a) Answer text with inline `[n]` cite chips and inline amber "Sources disagree" callout; (b) citation cards; (c) conflict cards; (d) refusal block. | Confirmed in mockup. Reads top-down: answer first, evidence next, caveats last. |
| 13 | Clearance badge palette | PUBLIC = green; RESTRICTED = amber; SECRET = red; TOP_SECRET = dark red. | Single Tailwind helper `lib/clearance-color.ts` so the palette is consistent across pages. |

---

## 2. Module layout

### 2.1 Backend additions

```
backend/app/
├── domain/
│   ├── chunk.py                       # unchanged; entities tuple already present
│   ├── conflict.py                    # NEW: Conflict, ConflictPair, Position value objects
│   └── chat.py                        # NEW: ChatRequest, ChatResponse, CitationOut, ConflictOut, Refusal
├── services/
│   ├── ingestion/
│   │   ├── entity_extractor.py        # NEW: spaCy wrapper. extract_entities(text) -> tuple[str, ...]
│   │   └── pipeline.py                # MODIFY: call extractor before ChunkRepository.bulk_insert
│   ├── conflict_detection/            # NEW package
│   │   ├── __init__.py                # detect_conflicts(results, llm) -> list[Conflict]
│   │   ├── prefilter.py               # build_candidate_pairs(results) -> list[ConflictPair]
│   │   ├── judge.py                   # judge_pair(pair, llm) -> Conflict | None  (cached)
│   │   └── prompts.py                 # JUDGE_PROMPT
│   ├── answer_generation/             # NEW package
│   │   ├── __init__.py                # generate_answer(query, chunks, conflicts, llm) -> AnswerWithCitations
│   │   ├── prompts.py                 # ANSWER_TEMPLATE, REFINE_TEMPLATE
│   │   └── llm_client.py              # LLMClient Protocol, GroqLLMClient with retry+fallback
│   └── retrieval/                     # unchanged from Phase B
├── api/
│   └── chat.py                        # NEW: POST /chat/ask router
├── repositories/
│   └── audit_repository.py            # MODIFY: + insert_response(...)
└── core/
    └── config.py                      # MODIFY: + groq_api_key, llm_primary_model, llm_fallback_model
```

### 2.2 Boundary rules

- **`services/conflict_detection/`** knows nothing about retrieval mechanics or answer generation. It accepts a `list[RetrievalResult]` and an `LLMClient`; returns `list[Conflict]`. Testable end-to-end with a `FakeLLMClient`.
- **`services/answer_generation/`** knows nothing about *how* chunks were retrieved or *how* conflicts were detected. It accepts the query string, chunks, conflicts, and an `LLMClient`; returns an `AnswerWithCitations` value object.
- **`LLMClient`** is a `typing.Protocol`, paralleling the `EmbeddingProvider` seam from Phase B. Production binding is `GroqLLMClient`; tests inject `FakeLLMClient` returning canned JSON for the judge and canned text for the synthesizer.
- **`entity_extractor.py`** exports a single function `extract_entities(text) -> tuple[str, ...]`. The spaCy `Language` object loads through an `@lru_cache` factory `get_default_extractor()` — same lazy-singleton pattern as `get_default_embedder()` in Phase B.
- **`POST /chat/ask`** is a thin orchestrator that depends on retrieval, conflict detection, and answer generation as services. No business logic in the router beyond timing, audit writes, and response assembly.

### 2.3 Schema impact

No new tables. No new columns. `chunks.entities TEXT[]` already exists from Phase B with default `[]`; this phase finally populates it. A one-time re-seed (`python scripts/seed_corpus.py`) repopulates all chunks. The seed script is idempotent (delete-by-source-prefix + reinsert), so no migration is needed.

The Phase B retrieval API (`POST /retrieval/search`) and all existing 88 tests remain untouched.

---

## 3. Conflict detection pipeline

### 3.1 Heuristic prefilter (`prefilter.py`)

Input: `list[RetrievalResult]` — the top-k=6 from Phase B retrieval.
Output: `list[ConflictPair]` — at most 4, ranked by ascending `a.rank + b.rank`.

A pair `(a, b)` where `a.chunk_id != b.chunk_id` becomes a candidate if **any** of:

1. `a.lineage_id == b.lineage_id` (lineage pair — handbook 2019 vs supplement 2023, reactor manual 2019 vs 2023, procurement 2020 vs 2024).
2. `a.department == b.department` and `|set(a.entities) ∩ set(b.entities)| >= 2` (same-department entity overlap).
3. `a.department != b.department` and `|set(a.entities) ∩ set(b.entities)| >= 3` (cross-department entity overlap — stricter threshold to control false positives from generic vocabulary overlap).

After collecting all candidates, sort by `a.rank + b.rank` ascending, take the first 4. Deduplicate by sorted pair-id tuple so the same pair never appears twice.

### 3.2 LLM judge (`judge.py`)

One Groq call per candidate pair. Prompt:

```
You are a conflict detector. Two passages from internal documents appear below.
Decide whether they make INCOMPATIBLE claims about the SAME subject.

A passage that adds detail to another, or discusses a different topic, is NOT a conflict.
Only flag genuine contradictions on the same subject.

PASSAGE_A — title: "{a.document_title}" · effective: {a.effective_date} · dept: {a.department}
{a.text}

PASSAGE_B — title: "{b.document_title}" · effective: {b.effective_date} · dept: {b.department}
{b.text}

Reply ONLY in JSON matching this schema:
{
  "conflict": true | false,
  "subject": "short noun phrase",
  "position_a": "one-sentence summary of A's claim on the subject",
  "position_b": "one-sentence summary of B's claim on the subject"
}
```

Groq is invoked with `response_format={"type": "json_object"}` so well-formed JSON is guaranteed. If `conflict == false`, `judge_pair` returns `None`. If JSON parsing fails (defensive), `judge_pair` logs at WARN and returns `None`.

### 3.3 Cache

```python
@lru_cache(maxsize=256)
def _judge_cached(pair_key: tuple[UUID, UUID]) -> Conflict | None: ...
```

`pair_key = (min(a.chunk_id, b.chunk_id), max(a.chunk_id, b.chunk_id))`. The cache wraps the *judge* call. The prefilter is cheap and re-runs on every query — caching it would be premature.

Cache is module-global, populated lazily, cleared on process restart. No TTL — chunks are immutable; their pair-conflict result is a stable property.

### 3.4 Orchestration (`__init__.py::detect_conflicts`)

```python
MAX_PAIRS_PER_QUERY = 4

async def detect_conflicts(
    *, results: list[RetrievalResult], llm: LLMClient
) -> list[Conflict]:
    pairs = build_candidate_pairs(results)[:MAX_PAIRS_PER_QUERY]
    judged = await asyncio.gather(*[judge_pair(p, llm) for p in pairs])
    return [c for c in judged if c is not None]
```

At most 4 concurrent Groq judge calls per query. The `GroqLLMClient` itself owns the retry-and-fallback ladder per individual call.

### 3.5 Failure mode summary

| Failure | Behavior |
|---|---|
| spaCy model not installed at ingest | Pipeline raises immediately; seed script fails loud (no silent empty `entities`). |
| Groq judge call exhausts both primary and fallback retries | `judge_pair` returns `None`; conflict silently excluded; answer-gen still proceeds. |
| Groq returns malformed JSON despite `json_object` mode | Logged WARN; returns `None`. |
| Zero candidate pairs after prefilter | Empty `list[Conflict]` returned. UI shows no conflict cards. |
| LRU cache full | Standard `functools.lru_cache` LRU eviction. |

---

## 4. Answer generation pipeline

### 4.1 LlamaIndex `CompactAndRefine` wiring

The synthesizer is constructed with a fully custom `text_qa_template` and `refine_template`. LlamaIndex retains responsibility for chunk batching and token-window accounting; the prompt content is entirely ours.

```python
from llama_index.core import PromptTemplate
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.llms.groq import Groq

synth = CompactAndRefine(
    llm=Groq(model=settings.llm_primary_model, api_key=settings.groq_api_key),
    text_qa_template=PromptTemplate(ANSWER_TEMPLATE),
    refine_template=PromptTemplate(REFINE_TEMPLATE),
    streaming=False,
)
```

At top-k=6 with ~512-token chunks (~3K total context), all chunks fit in one batch, so the refine template is rarely exercised. It is still provided so the synthesizer is well-formed if a future chunk-size adjustment in Phase D pushes context into multi-batch territory.

### 4.2 Answer template (`prompts.py::ANSWER_TEMPLATE`)

```
You are HOLOCRON, an enterprise knowledge assistant for the Imperial archives.
Answer the user's question using ONLY the numbered context blocks below.

Rules:
- Cite every claim with inline markers like [1], [2]. A claim may have multiple markers.
- Do NOT use information not present in the context.
- If the context is insufficient to answer, say so explicitly.
- When the CONFLICTS section is present, acknowledge the disagreement with phrasing such as:
  "Sources disagree: [n] states X; [m] states Y."
- Be concise. 3 to 5 sentences for typical questions.

CONTEXT:
[1] (clearance: {classification}, dept: {department}, effective: {effective_date}, doc: "{document_title}")
{text}

[2] (clearance: ..., ...)
{text}
...

CONFLICTS (already detected by a separate process; cite the markers shown):
- Subject: {subject}
  [{a_marker}] states: {position_a}
  [{b_marker}] states: {position_b}
...

QUESTION: {query_str}

ANSWER:
```

`{a_marker}` and `{b_marker}` are computed at template-render time: the index of each conflicting chunk in the CONTEXT block (1-based). When `conflicts` is empty, the CONFLICTS section is omitted entirely.

### 4.3 Refine template

Standard LlamaIndex refine shape — preserve any existing answer, extend with additional context, preserve `[n]` citation markers, do not introduce new claims. Not exercised at top-k=6 today; present for future-proofing.

### 4.4 Citation post-parsing

After the synthesizer returns answer text, parse inline `[n]` markers and resolve them to chunk IDs:

```python
cited_idxs = sorted({int(m) for m in re.findall(r"\[(\d+)\]", answer_text)})
cited_chunk_ids = [
    chunks[i - 1].chunk_id
    for i in cited_idxs
    if 1 <= i <= len(chunks)
]
```

Out-of-range markers (e.g. `[99]`) are dropped silently and logged at WARN. Only chunks whose markers appear in `cited_chunk_ids` are surfaced as citation cards in the API response — uncited retrieved chunks remain visible only in the audit row.

### 4.5 Groq LLM client (`llm_client.py`)

```python
class LLMClient(Protocol):
    async def complete_json(self, prompt: str) -> dict: ...   # used by the judge
    async def complete_text(self, prompt: str) -> str: ...    # used by the synthesizer wrapper

class GroqLLMClient:
    primary: str   # llama-3.3-70b-versatile
    fallback: str  # llama-3.1-8b-instant
    # async retry ladder per call:
    #   primary attempts 1..3 with backoff 0.5s, 1s, 2s
    #   fallback attempts 1..3 with backoff 0.5s, 1s, 2s
    # all six exhausted -> raise LLMUnavailable
```

The judge uses `complete_json`. The synthesizer call path must apply the **same** retry-and-fallback policy. Implementation choice (wrap the LlamaIndex `Groq` LLM with a retry decorator, or call our `GroqLLMClient.complete_text` from a thin custom synthesizer instead of LlamaIndex's, or any equivalent) is deferred to the implementation plan; the contract is that any `Groq` HTTP path emits at most 6 attempts (3 primary, 3 fallback) before raising `LLMUnavailable`.

### 4.6 Failure mode summary

| Failure | Behavior |
|---|---|
| All retries fail on judge | Conflict service returns `[]`; answer still generated. |
| All retries fail on synthesizer | `POST /chat/ask` returns 503; UI shows retry banner. |
| LLM emits `[99]` (out-of-range marker) | Filtered by index check; logged WARN. |
| LLM emits zero markers | Answer returned as-is; `cited_chunk_ids = []`; UI shows subtle "No citations attached" hint. |

---

## 5. `POST /chat/ask` API contract

### 5.1 Request

```json
POST /chat/ask
Cookie: holocron_session=<jwt>
Content-Type: application/json

{
  "query": "What's the dress-code policy for off-base events?",
  "top_k": 6
}
```

`top_k` is optional, defaults to 6, maximum 10. Auth is the existing JWT cookie from Phase A; the `get_current_user` dependency yields the `User` row, from which `tenant_id`, `max_clearance`, and `departments` are derived for the `ClearanceContext`. No `tenant_id` is accepted in the request body.

### 5.2 Successful response (200)

```json
{
  "query": "What's the dress-code policy for off-base events?",
  "answer": {
    "text": "The Imperial Employee Handbook requires regulation uniform [1] ... Sources disagree: [1] prohibits insignia off-base; [2] permits unit insignia for senior staff.",
    "cited_chunk_ids": ["<uuid>", "<uuid>"]
  },
  "citations": [
    {
      "marker": 1,
      "chunk_id": "<uuid>",
      "document_id": "<uuid>",
      "document_title": "Imperial Employee Handbook",
      "classification": "public",
      "department": "hr",
      "effective_date": "2019-03-15",
      "snippet": "All personnel attending off-base functions shall wear regulation uniform..."
    },
    { "marker": 2, "...": "..." }
  ],
  "conflicts": [
    {
      "subject": "Off-duty unit insignia",
      "position_a": { "marker": 1, "text": "...insignia removed during all off-base events." },
      "position_b": { "marker": 2, "text": "...senior staff may retain unit insignia at official functions." }
    }
  ],
  "refusal": {
    "reference_id": "MGMO-C65Q",
    "withheld_count": 6
  }
}
```

Contract details:

- `citations` includes only chunks whose marker appears in `answer.text`, in marker order. Retrieved-but-uncited chunks do not appear in the payload (they remain in the audit row).
- `conflicts[].position_a.marker` and `position_b.marker` reference the same numbering as `citations[].marker` and the inline `[n]` chips in `answer.text`. The frontend uses these markers to link conflict-card sides to their citation card via hash anchors.
- `refusal` is `null` when `withheld_count == 0`; otherwise it carries the reference ID and withheld count. The frontend tests `response.refusal != null` before rendering the refusal block.
- `conflicts` is an empty array `[]` (never `null`) when no conflicts are detected.

### 5.3 Error responses

| Status | When | Body |
|---|---|---|
| 400 | Empty or whitespace-only `query`; `top_k > 10` | `{"detail":"<specific reason>"}` |
| 401 | Missing or invalid `holocron_session` cookie | `{"detail":"Not authenticated"}` (existing Phase A behavior) |
| 503 | All Groq retries fail on answer generation | `{"detail":"LLM temporarily unavailable. Please retry."}` |

An out-of-clearance query never returns 4xx. It returns 200 with `citations` containing only clearance-permitted chunks and `refusal` populated. This is the honest-refusal contract from Phase B.

### 5.4 Audit log writes

A single `POST /chat/ask` invocation writes up to three audit rows:

1. `query` event (existing Phase B helper) — `query_text`, `retrieved_ids` (all top-k, including cited and uncited), `latency_ms`.
2. `refusal` event (existing Phase B helper) — only when `refusal != null`.
3. `response` event (NEW in Phase C) — `response_text`, `conflicts_found` JSONB, `latency_ms`. `AuditRepository.insert_response(...)` is added.

### 5.5 Orchestration code shape

```python
@router.post("/chat/ask", response_model=ChatResponse)
async def ask(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    embedder: EmbeddingProvider = Depends(get_default_embedder),
    llm: LLMClient = Depends(get_default_llm),
) -> ChatResponse:
    ctx = ClearanceContext.from_user(user)
    t0 = perf_counter()

    search_resp = await retrieval.search(
        session=session, ctx=ctx, embedder=embedder, query=body.query, top_k=body.top_k
    )
    conflicts = await conflict_detection.detect_conflicts(
        results=list(search_resp.results), llm=llm
    )
    answer = await answer_generation.generate_answer(
        query=body.query, chunks=list(search_resp.results), conflicts=conflicts, llm=llm
    )

    latency_ms = int((perf_counter() - t0) * 1000)
    # audit.insert_response(...) here
    return assemble_chat_response(...)
```

---

## 6. Frontend `/chat`

### 6.1 Page structure

```
frontend/app/chat/
├── page.tsx                  # 'use client'; auth gate via /me; renders thread + input
├── components/
│   ├── ChatThread.tsx
│   ├── MessageUser.tsx
│   ├── MessageAssistant.tsx
│   ├── CitationCard.tsx
│   ├── ConflictCard.tsx
│   ├── RefusalNote.tsx
│   ├── ChatInput.tsx
│   └── ClearanceBadge.tsx
└── lib/
    ├── chat-api.ts           # postChatAsk(query): Promise<ChatResponse>
    └── clearance-color.ts    # classification -> Tailwind classes
```

### 6.2 React state shape

```ts
type Turn =
  | { role: 'user'; query: string; id: string }
  | { role: 'assistant'; payload: ChatResponse; id: string }
  | { role: 'assistant-pending'; id: string }
  | { role: 'assistant-error'; message: string; previousQuery: string; id: string };

const [turns, setTurns] = useState<Turn[]>([]);
const [sending, setSending] = useState(false);
```

Submitting a query appends `{role: 'user'}` and `{role: 'assistant-pending'}`, fires `postChatAsk`, and on resolution replaces the pending entry with either the full assistant turn or an `assistant-error` entry. Page reload clears `turns`. There is no localStorage, URL state, or DB persistence.

### 6.3 Authentication and redirect

On mount, `page.tsx` calls the existing `GET /me` endpoint. A 401 response triggers `router.replace('/login?next=/chat')`. A 200 response renders the chat thread with a thin header strip showing the user's display name + clearance badge + departments.

### 6.4 Inline citation rendering

The answer text contains literal `[1]`, `[2]` markers. `MessageAssistant.tsx` splits the text on `/(\[\d+\])/`, wraps each marker in a styled `<a href="#cite-{n}">` chip, and renders the rest as text. Each citation card has `id="cite-{marker}"`, so clicking a chip scrolls to the matching card. The same hash-anchor mechanism is used by `ConflictCard.tsx` for its two side headers.

### 6.5 Styling

Tailwind + shadcn/ui. shadcn primitives used: `Card`, `Badge`, `Button`, `Textarea`. The conflict-card colors are inline Tailwind classes (`bg-red-50`, `border-red-200`). `lib/clearance-color.ts` maps `'public' | 'restricted' | 'secret' | 'top_secret'` to badge color classes so the palette is uniform across the page.

### 6.6 Loading and empty states

- **Empty thread:** centered card showing the user's clearance and departments, plus two suggested-question chips that prefill the textarea — one per headline demo (dress code, reactor shutdown).
- **Pending:** a skeleton message bubble with a subtle pulse animation. Typical latency 3–7 seconds.
- **Error:** a red-bordered card "LLM temporarily unavailable. Please retry." with a button that re-sends the previous user query.

### 6.7 Frontend tests

Not a Phase C priority. The verification gate is **manual reproduction of both headline demos in the browser** (see §7.1). Frontend test infrastructure is deferred — neither the design spec nor the MVP budget includes it.

---

## 7. Exit criteria, risks, definition-of-done

### 7.1 End-of-phase demo checklist

Phase C is done when **all** of these reproduce manually in the browser without code changes:

- [ ] `pnpm dev` + `uvicorn` running; navigate to `/chat`.
- [ ] **Demo A — executive view.** Log in as `executive.procurement`. Ask "What's the dress-code policy for off-base events?" Receive an answer citing `[1]` *Imperial Employee Handbook* and `[2]` *Management Conduct Supplement*. A conflict card appears for "off-duty unit insignia." No refusal block (procurement + hr clearance covers both documents).
- [ ] **Demo A — employee view.** Log out, log in as `employee.security`. Ask the same question. Receive an answer citing only PUBLIC chunks. The refusal block is populated with `withheld_count > 0` and a reference ID. No conflict card.
- [ ] **Demo B — director view.** Log in as `director.engineering`. Ask "What is the reactor coolant shutdown sequence?" Receive an answer citing both `reactor_manual_2019` and `reactor_manual_2023`. A conflict card appears for the shutdown-sequence disagreement. The answer prose contains "Sources disagree..." phrasing.
- [ ] **Demo B — employee view.** Log in as `employee.security`. Ask the same question. Receive a refusal block; no engineering citations.
- [ ] Inline `[n]` chips in any answer scroll to their matching citation card on click.
- [ ] All Phase A + Phase B tests still pass; Phase C tests pass; suite remains under ~30s default (without slow tests).
- [ ] `audit_events` contains `query`, `response`, and (where applicable) `refusal` rows for each demo question, with non-empty `retrieved_ids` and `conflicts_found` JSONB.

### 7.2 Test suite target

Phase C adds approximately:

- ~8 unit tests: `test_prefilter`, `test_judge_cache`, `test_entity_extractor`, `test_citation_parse`, `test_answer_prompt_render`.
- ~4 service tests: `test_conflict_detection` (fake LLM), `test_answer_generation` (fake LLM).
- ~4 API tests: `test_chat_endpoint`, `test_chat_auth`, `test_chat_validation`.
- ~2 slow tests (opt-in, `@pytest.mark.slow`): `test_real_spacy_extraction`, `test_real_groq_judge_and_answer`.

Target: **~104 total tests passing in under ~30 seconds default run**, plus the slow tests opt-in via `pytest -m slow`.

### 7.3 Risks and mitigations

| Risk | Mitigation |
|---|---|
| Groq free-tier rate-limits hit mid-demo | Two-model fallback (70b → 8b) with 3 retries each = 6 attempts before user sees an error. |
| spaCy install on Windows is sometimes flaky | Document `python -m spacy download en_core_web_sm` as a one-time install step in CLAUDE.md; pin spaCy minor version. |
| Conflict false positives clutter the UI | Stricter cross-department entity threshold (3 vs 2); judge prompt explicitly rejects "different topic" pairs. |
| LLM emits answer with no citation markers | Logged WARN; UI shows subtle hint; Phase D eval flags as a regression. |
| Re-seeding the corpus to populate entities adds 30–60 seconds | Acceptable. `scripts/seed_corpus.py` is already idempotent. |
| `CompactAndRefine` shape changes on LlamaIndex minor upgrade | Pin LlamaIndex minor version in `pyproject.toml`; document in CLAUDE.md follow-ups. |
| First `/chat/ask` after restart still slow due to lazy BGE load | Acceptable for Phase C — same as Phase B. Phase D may warm at startup. |
| Empty or whitespace query submitted | API returns 400; UI disables Send button while textarea is empty or whitespace-only. |

### 7.4 Definition-of-done checklist

- [ ] All §7.1 demo paths reproduce in the browser.
- [ ] Test suite hits ~104 passing in under ~30 seconds default; 2 slow tests pass via `pytest -m slow`.
- [ ] `pyproject.toml` lists new dependencies: `spacy>=3.7,<4`, `llama-index-llms-groq>=0.2,<0.3`, `groq>=0.13,<0.14`.
- [ ] `backend/.env.example` adds `GROQ_API_KEY`, `LLM_PRIMARY_MODEL`, `LLM_FALLBACK_MODEL`.
- [ ] CLAUDE.md updated: spaCy install step in the Local dev quickstart; Phase C completion record path; Phase D handoff section.
- [ ] Phase C completion record committed at `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`.

---

## 8. Out-of-scope confirmations (carried to Phase D)

- `/admin/documents` (upload form + list).
- `/admin/audit` viewer.
- Disk cache for Groq responses (the on-disk content-addressed cache discussed during brainstorming).
- structlog → JSON stdout.
- Evaluation harness, `golden_set.yaml`, `make eval`.
- arq + Redis re-embed worker.
- Streaming responses.

These remain in the parent design spec under Phase D.
