# Phase C — Conflict Detection + Chat Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase C end-to-end: entity extraction at ingest, heuristic + LLM-judge conflict detection with LRU caching, LlamaIndex `CompactAndRefine` answer synthesis with citation parsing, `POST /chat/ask` endpoint, and the `/chat` frontend so both headline demos reproduce in the browser.

**Architecture:** Add three services (`entity_extractor`, `conflict_detection/*`, `answer_generation/*`) and a single new API router. Reuse Phase B retrieval untouched. Frontend is a single in-page chat-thread route with React-only state. LLM access goes through a `LLMClient` Protocol for the judge path and a LlamaIndex synthesizer factory for the answer path; tests inject fakes for both.

**Tech Stack:** Python 3.11 · FastAPI · async SQLAlchemy 2.x · spaCy 3.x (`en_core_web_sm`) · LlamaIndex `CompactAndRefine` + `llama-index-llms-groq` · Groq API · Next.js 15 · React 19 · TypeScript · Tailwind + shadcn/ui.

**Source spec:** [docs/superpowers/specs/2026-06-28-phase-c-conflict-detection-chat.md](../specs/2026-06-28-phase-c-conflict-detection-chat.md)

---

## File map

**Backend — new:**

- `backend/app/domain/conflict.py` — `Position`, `ConflictPair`, `Conflict` value objects
- `backend/app/services/ingestion/entity_extractor.py` — `extract_entities(text)`; `get_default_extractor()` factory
- `backend/app/services/conflict_detection/__init__.py` — `detect_conflicts(...)` orchestrator
- `backend/app/services/conflict_detection/prefilter.py` — `build_candidate_pairs(...)`
- `backend/app/services/conflict_detection/judge.py` — `judge_pair(...)` with `lru_cache`
- `backend/app/services/conflict_detection/prompts.py` — `JUDGE_PROMPT`
- `backend/app/services/answer_generation/__init__.py` — `generate_answer(...)`, `AnswerWithCitations` dataclass
- `backend/app/services/answer_generation/prompts.py` — `ANSWER_TEMPLATE`, `REFINE_TEMPLATE`, `render_context_block(...)`, `render_conflicts_block(...)`
- `backend/app/services/answer_generation/citations.py` — `parse_citation_markers(text)`
- `backend/app/services/answer_generation/llm_client.py` — `LLMClient` Protocol, `FakeLLMClient`, `GroqLLMClient`, `LLMUnavailable`, `get_default_llm()` factory
- `backend/app/services/answer_generation/synthesizer.py` — `get_default_synthesizer()` factory returning a configured LlamaIndex `CompactAndRefine`
- `backend/app/api/chat.py` — `POST /chat/ask` router

**Backend — modified:**

- `backend/app/services/ingestion/pipeline.py` — call `extract_entities` per chunk before `bulk_insert`
- `backend/app/repositories/audit_repository.py` — `insert_response(...)`
- `backend/app/core/config.py` — `groq_api_key`, `llm_primary_model`, `llm_fallback_model`
- `backend/app/api/schemas.py` — `ChatRequest`, `ChatResponse`, `CitationOut`, `ConflictOut`, `PositionOut`, `AnswerOut`, `RefusalOut`
- `backend/app/main.py` — register `chat_router`
- `backend/pyproject.toml` — add deps
- `backend/.env.example` — add Groq + LLM env vars

**Backend — tests (new):**

- `backend/tests/test_entity_extractor.py`
- `backend/tests/test_entity_extractor_real.py` (slow)
- `backend/tests/test_ingestion_pipeline_entities.py`
- `backend/tests/test_llm_client.py`
- `backend/tests/test_conflict_prefilter.py`
- `backend/tests/test_conflict_judge.py`
- `backend/tests/test_conflict_detection.py`
- `backend/tests/test_answer_prompts.py`
- `backend/tests/test_citations.py`
- `backend/tests/test_answer_generation.py`
- `backend/tests/test_chat_endpoint.py`
- `backend/tests/test_chat_endpoint_real_groq.py` (slow)

**Frontend — new:**

- `frontend/app/chat/page.tsx`
- `frontend/app/chat/components/ChatThread.tsx`
- `frontend/app/chat/components/MessageUser.tsx`
- `frontend/app/chat/components/MessageAssistant.tsx`
- `frontend/app/chat/components/CitationCard.tsx`
- `frontend/app/chat/components/ConflictCard.tsx`
- `frontend/app/chat/components/RefusalNote.tsx`
- `frontend/app/chat/components/ChatInput.tsx`
- `frontend/components/ClearanceBadge.tsx`
- `frontend/lib/chat-api.ts`
- `frontend/lib/clearance-color.ts`
- `frontend/lib/types/chat.ts`

**Docs — modified:**

- `CLAUDE.md` — spaCy install note in quickstart; Phase C status; Phase D handoff
- `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md` (new at end)

---

## Task 0: Dependencies, settings, environment

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example` (create if missing)

- [ ] **Step 1: Add backend deps**

Open `backend/pyproject.toml` and add the following lines to `[project].dependencies` (preserving alphabetical-ish grouping, after the Phase B block):

```toml
    # Phase C
    "spacy>=3.7,<4.0",
    "groq>=0.13,<0.14",
    "llama-index-llms-groq>=0.2,<0.3",
```

- [ ] **Step 2: Install deps and spaCy model**

Run (PowerShell, with venv active):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

Expected: pip resolves cleanly; `Successfully installed en-core-web-sm-3.x.x` from the spaCy model download.

- [ ] **Step 3: Add Settings fields**

Edit `backend/app/core/config.py` and add three new fields to the `Settings` class, after `cors_origins`:

```python
    groq_api_key: str = ""
    llm_primary_model: str = "llama-3.3-70b-versatile"
    llm_fallback_model: str = "llama-3.1-8b-instant"
```

The empty-string default for `groq_api_key` lets the test suite import `Settings()` without a real key (judge/answer tests use fakes); production fails at first LLM call rather than at import time.

- [ ] **Step 4: Update `.env.example`**

Create or edit `backend/.env.example`. Ensure it contains (append if existing):

```
# Phase C - Groq
GROQ_API_KEY=
LLM_PRIMARY_MODEL=llama-3.3-70b-versatile
LLM_FALLBACK_MODEL=llama-3.1-8b-instant
```

- [ ] **Step 5: Verify existing tests still pass**

Run:

```powershell
python -m pytest -v
```

Expected: 88 passing, 2 deselected (Phase B baseline). No regressions.

- [ ] **Step 6: Commit**

```powershell
git add backend/pyproject.toml backend/app/core/config.py backend/.env.example
git commit -m "chore(phase-c): add spacy/groq/llama-index-llms-groq deps and LLM settings"
```

---

## Task 1: Domain value objects — `conflict.py`

**Files:**
- Create: `backend/app/domain/conflict.py`
- Create: `backend/tests/test_domain_conflict.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_domain_conflict.py`:

```python
from __future__ import annotations

import uuid

from app.domain.conflict import Conflict, ConflictPair, Position


def test_conflict_pair_is_hashable_and_orderless():
    a = uuid.uuid4()
    b = uuid.uuid4()
    p1 = ConflictPair(chunk_a_id=a, chunk_b_id=b, a_rank=1, b_rank=2)
    p2 = ConflictPair(chunk_a_id=b, chunk_b_id=a, a_rank=2, b_rank=1)
    # Same underlying pair must produce the same canonical key
    assert p1.canonical_key() == p2.canonical_key()
    assert p1.rank_sum() == 3
    assert p2.rank_sum() == 3


def test_conflict_payload_immutable():
    cid_a = uuid.uuid4()
    cid_b = uuid.uuid4()
    c = Conflict(
        subject="Off-duty unit insignia",
        position_a=Position(marker=1, chunk_id=cid_a, text="A says..."),
        position_b=Position(marker=2, chunk_id=cid_b, text="B says..."),
    )
    assert c.subject == "Off-duty unit insignia"
    assert c.position_a.marker == 1
    assert c.position_b.text == "B says..."
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_domain_conflict.py -v
```

Expected: `ImportError: cannot import name 'Conflict' from 'app.domain.conflict'`.

- [ ] **Step 3: Implement `conflict.py`**

Create `backend/app/domain/conflict.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    marker: int
    chunk_id: uuid.UUID
    text: str


@dataclass(frozen=True)
class ConflictPair:
    """A candidate pair surfaced by the heuristic prefilter, before judging."""

    chunk_a_id: uuid.UUID
    chunk_b_id: uuid.UUID
    a_rank: int
    b_rank: int

    def canonical_key(self) -> tuple[uuid.UUID, uuid.UUID]:
        lo, hi = sorted((self.chunk_a_id, self.chunk_b_id))
        return (lo, hi)

    def rank_sum(self) -> int:
        return self.a_rank + self.b_rank


@dataclass(frozen=True)
class Conflict:
    subject: str
    position_a: Position
    position_b: Position
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/test_domain_conflict.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domain/conflict.py backend/tests/test_domain_conflict.py
git commit -m "feat(domain): Conflict, ConflictPair, Position value objects"
```

---

## Task 2: Entity extractor — spaCy wrapper

**Files:**
- Create: `backend/app/services/ingestion/entity_extractor.py`
- Create: `backend/tests/test_entity_extractor.py`
- Create: `backend/tests/test_entity_extractor_real.py`

- [ ] **Step 1: Write failing unit test**

Create `backend/tests/test_entity_extractor.py`:

```python
from __future__ import annotations

from app.services.ingestion.entity_extractor import (
    extract_entities,
    _extract_from_doc,  # noqa: F401  helper used in test below
)


class _FakeToken:
    def __init__(self, lemma_: str, is_stop: bool = False, is_punct: bool = False) -> None:
        self.lemma_ = lemma_
        self.is_stop = is_stop
        self.is_punct = is_punct


class _FakeChunk:
    def __init__(self, tokens: list[_FakeToken], text: str) -> None:
        self.tokens = tokens
        self._text = text

    def __iter__(self):
        return iter(self.tokens)

    @property
    def text(self) -> str:
        return self._text


class _FakeEnt:
    def __init__(self, text: str, label_: str) -> None:
        self.text = text
        self.label_ = label_


class _FakeDoc:
    def __init__(self, noun_chunks: list[_FakeChunk], ents: list[_FakeEnt]) -> None:
        self.noun_chunks = noun_chunks
        self.ents = ents


def test_extracts_lemma_lower_noun_chunks_dedup():
    doc = _FakeDoc(
        noun_chunks=[
            _FakeChunk(
                [_FakeToken("audit"), _FakeToken("cadence")],
                "Audit Cadence",
            ),
            _FakeChunk(
                [_FakeToken("Audit"), _FakeToken("cadence")],
                "audit cadence",
            ),
            _FakeChunk(
                [_FakeToken("the", is_stop=True), _FakeToken("incident")],
                "the incident",
            ),
        ],
        ents=[_FakeEnt("Death Star", "ORG"), _FakeEnt("2023", "DATE")],
    )
    out = _extract_from_doc(doc)
    # Duplicates collapsed, stop-words dropped, NER preserved verbatim-lowered
    assert "audit cadence" in out
    assert "incident" in out
    assert "death star" in out
    assert "2023" in out
    # No duplicates
    assert len(out) == len(set(out))


def test_empty_text_returns_empty_tuple(monkeypatch):
    import app.services.ingestion.entity_extractor as ee

    def fake_loader():
        class _NL:
            def __call__(self, _text):
                return _FakeDoc(noun_chunks=[], ents=[])
        return _NL()

    monkeypatch.setattr(ee, "_load_spacy", fake_loader)
    monkeypatch.setattr(ee, "_nlp", None)  # force reload
    out = extract_entities("   ")
    assert out == ()
```

- [ ] **Step 2: Run unit tests to verify failure**

```powershell
python -m pytest tests/test_entity_extractor.py -v
```

Expected: `ImportError` or attribute-not-found.

- [ ] **Step 3: Implement `entity_extractor.py`**

Create `backend/app/services/ingestion/entity_extractor.py`:

```python
from __future__ import annotations

from typing import Any

_MODEL_NAME = "en_core_web_sm"
_nlp: Any | None = None


def _load_spacy() -> Any:
    import spacy  # heavy import; defer

    return spacy.load(_MODEL_NAME, disable=["parser", "lemmatizer"])  # keep tagger + ner

# > **Shipped deviation (Phase D doc update, 2026-06-28):** the `disable=[...]` argument
# > was removed during Phase C execution. `parser` is required for `doc.noun_chunks`
# > (raises `E029` otherwise); `lemmatizer` is required for `token.lemma_` to return
# > non-empty strings. The full default pipeline is loaded.


def get_default_extractor() -> Any:
    """Cached singleton — spaCy model loads once per process."""
    global _nlp
    if _nlp is None:
        _nlp = _load_spacy()
    return _nlp


def _extract_from_doc(doc: Any) -> tuple[str, ...]:
    seen: list[str] = []
    seen_set: set[str] = set()

    def add(term: str) -> None:
        t = term.strip().lower()
        if not t:
            return
        if t in seen_set:
            return
        seen_set.add(t)
        seen.append(t)

    # Noun chunks: drop stop/punct tokens; join remaining token lemmas
    for chunk in doc.noun_chunks:
        toks = [tok.lemma_.lower() for tok in chunk if not tok.is_stop and not tok.is_punct]
        if toks:
            add(" ".join(toks))

    # Named entities: keep verbatim (lowered)
    for ent in doc.ents:
        add(ent.text)

    return tuple(seen)


def extract_entities(text: str) -> tuple[str, ...]:
    if not text or not text.strip():
        return ()
    nlp = get_default_extractor()
    doc = nlp(text)
    return _extract_from_doc(doc)
```

Note: `_load_spacy` disables the parser and lemmatizer pipelines. Lemmas still come from the tagger via `token.lemma_` after the tagger runs (modern spaCy default). If model behavior differs, the slow test in Step 5 catches it.

- [ ] **Step 4: Run unit tests**

```powershell
python -m pytest tests/test_entity_extractor.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Write slow test against real spaCy**

Create `backend/tests/test_entity_extractor_real.py`:

```python
from __future__ import annotations

import pytest

from app.services.ingestion.entity_extractor import extract_entities


@pytest.mark.slow
def test_real_spacy_extracts_meaningful_entities():
    text = (
        "All Death Star personnel must complete the quarterly audit cadence review "
        "by 2023-12-15. Incident response procedures fall under Security oversight."
    )
    ents = extract_entities(text)
    assert any("audit" in e for e in ents)
    assert any("incident" in e for e in ents)
    assert any("death star" in e for e in ents)
```

- [ ] **Step 6: Run slow test**

```powershell
python -m pytest tests/test_entity_extractor_real.py -v -m slow
```

Expected: 1 passed.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/ingestion/entity_extractor.py backend/tests/test_entity_extractor.py backend/tests/test_entity_extractor_real.py
git commit -m "feat(ingestion): spaCy entity extractor with noun-chunk + NER union"
```

---

## Task 3: Wire entity extractor into pipeline; re-seed corpus

**Files:**
- Modify: `backend/app/services/ingestion/pipeline.py`
- Create: `backend/tests/test_ingestion_pipeline_entities.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_ingestion_pipeline_entities.py`:

```python
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.domain.models import Chunk, Tenant
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.pipeline import ingest_corpus_dir


@pytest.mark.asyncio
async def test_pipeline_populates_entities_from_chunk_text(
    db_session, empire_tenant: Tenant, tmp_path: Path, monkeypatch
):
    # Stub extractor: produces a deterministic two-entity tuple per text
    import app.services.ingestion.pipeline as pl

    calls: list[str] = []

    def fake_extract(text: str) -> tuple[str, ...]:
        calls.append(text)
        return ("audit cadence", "incident response")

    monkeypatch.setattr(pl, "extract_entities", fake_extract)

    doc_dir = tmp_path / "mini"
    doc_dir.mkdir()
    (doc_dir / "doc.md").write_text(
        "---\n"
        "title: Test Doc\n"
        "classification: public\n"
        "department: hr\n"
        "version: '1.0'\n"
        "effective_date: 2024-01-01\n"
        "lineage_id: test-doc\n"
        "---\n"
        "Quarterly audits matter. Incident reviews happen monthly."
    )

    await ingest_corpus_dir(
        corpus_dir=doc_dir,
        tenant_id=empire_tenant.id,
        session=db_session,
        embedder=FakeEmbeddingProvider(),
    )
    await db_session.flush()

    rows = (await db_session.execute(select(Chunk))).scalars().all()
    assert rows, "expected at least one chunk inserted"
    for c in rows:
        assert list(c.entities) == ["audit cadence", "incident response"]
    assert len(calls) == len(rows)
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_ingestion_pipeline_entities.py -v
```

Expected: AssertionError — `c.entities` is `[]` because pipeline doesn't extract yet.

- [ ] **Step 3: Modify pipeline to call the extractor**

Edit `backend/app/services/ingestion/pipeline.py`. Replace the import block and `_build_doc_and_chunks` to call `extract_entities` per chunk text:

At the top, add the import:

```python
from app.services.ingestion.entity_extractor import extract_entities
```

In `_build_doc_and_chunks`, replace the chunk list comprehension with one that populates `entities`:

```python
    chunks = [
        Chunk(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            document_id=doc_id,
            ordinal=i,
            text_=text,
            embedding=vec.tolist(),
            classification=fm.classification,
            department=fm.department,
            effective_date=fm.effective_date,
            lineage_id=lineage,
            entities=list(extract_entities(text)),
        )
        for i, (text, vec) in enumerate(zip(chunk_texts, vectors))
    ]
```

- [ ] **Step 4: Run test**

```powershell
python -m pytest tests/test_ingestion_pipeline_entities.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Run full default suite**

```powershell
python -m pytest -v
```

Expected: all Phase B + Phase C tests so far pass.

- [ ] **Step 6: Re-seed corpus to populate entities on the real DB**

Run:

```powershell
python scripts/seed_corpus.py
```

Expected: completes in ~60-120 s; final message includes "documents_inserted=18, chunks_inserted=~39".

Then verify in psql or a one-off script:

```powershell
psql -h localhost -p 5433 -U postgres -d holocron -c "SELECT count(*) FROM chunks WHERE array_length(entities, 1) > 0;"
```

Expected: count equals total chunk count (~39).

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/ingestion/pipeline.py backend/tests/test_ingestion_pipeline_entities.py
git commit -m "feat(ingestion): populate chunks.entities via spaCy at ingest"
```

---

## Task 4: LLM client — Protocol, Fake, Groq, retry/fallback

**Files:**
- Create: `backend/app/services/answer_generation/__init__.py` (empty package marker for now)
- Create: `backend/app/services/answer_generation/llm_client.py`
- Create: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Create the answer_generation package marker**

Create `backend/app/services/answer_generation/__init__.py` with a single line:

```python
"""Answer generation service — populated in later tasks."""
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_llm_client.py`:

```python
from __future__ import annotations

import pytest

from app.services.answer_generation.llm_client import (
    FakeLLMClient,
    GroqLLMClient,
    LLMUnavailable,
)


@pytest.mark.asyncio
async def test_fake_returns_scripted_json():
    fake = FakeLLMClient(json_responses=[{"conflict": True, "subject": "x"}])
    out = await fake.complete_json("any prompt")
    assert out == {"conflict": True, "subject": "x"}
    assert fake.calls_json == ["any prompt"]


@pytest.mark.asyncio
async def test_fake_returns_scripted_text():
    fake = FakeLLMClient(text_responses=["hello [1] world"])
    out = await fake.complete_text("any prompt")
    assert out == "hello [1] world"
    assert fake.calls_text == ["any prompt"]


@pytest.mark.asyncio
async def test_fake_exhausting_responses_raises():
    fake = FakeLLMClient()
    with pytest.raises(IndexError):
        await fake.complete_json("p")


@pytest.mark.asyncio
async def test_groq_client_retries_then_falls_back(monkeypatch):
    """Wire a fake httpx-style 429 transport to assert the retry ladder."""

    attempts: list[str] = []

    class _FakeAPIError(Exception):
        def __init__(self, status: int):
            self.status = status

    async def fake_call(self, *, model: str, prompt: str, json_mode: bool):
        attempts.append(model)
        if model == self.primary:
            raise _FakeAPIError(429)
        # fallback succeeds on first attempt
        return "ok"

    monkeypatch.setattr(GroqLLMClient, "_raw_call", fake_call, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_is_rate_limit", lambda self, e: isinstance(e, _FakeAPIError) and e.status == 429, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_sleep", lambda self, _s: None, raising=False)

    c = GroqLLMClient(api_key="x", primary="prim", fallback="fb")
    out = await c.complete_text("p")
    assert out == "ok"
    # 3 attempts on primary, then 1 successful on fallback
    assert attempts == ["prim", "prim", "prim", "fb"]


@pytest.mark.asyncio
async def test_groq_raises_when_all_attempts_fail(monkeypatch):
    class _FakeAPIError(Exception):
        def __init__(self, status: int):
            self.status = status

    async def fake_call(self, *, model: str, prompt: str, json_mode: bool):
        raise _FakeAPIError(429)

    monkeypatch.setattr(GroqLLMClient, "_raw_call", fake_call, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_is_rate_limit", lambda self, e: True, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_sleep", lambda self, _s: None, raising=False)

    c = GroqLLMClient(api_key="x", primary="prim", fallback="fb")
    with pytest.raises(LLMUnavailable):
        await c.complete_text("p")
```

- [ ] **Step 3: Run tests to verify failure**

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `llm_client.py`**

Create `backend/app/services/answer_generation/llm_client.py`:

```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings


class LLMUnavailable(Exception):
    """Raised when all retry+fallback attempts have failed."""


class LLMClient(Protocol):
    async def complete_json(self, prompt: str) -> dict: ...
    async def complete_text(self, prompt: str) -> str: ...


@dataclass
class FakeLLMClient:
    """Scripted in-process LLM stand-in for tests.

    json_responses and text_responses are popped in order on each call.
    """

    json_responses: list[dict] = field(default_factory=list)
    text_responses: list[str] = field(default_factory=list)
    calls_json: list[str] = field(default_factory=list)
    calls_text: list[str] = field(default_factory=list)

    async def complete_json(self, prompt: str) -> dict:
        self.calls_json.append(prompt)
        return self.json_responses.pop(0)

    async def complete_text(self, prompt: str) -> str:
        self.calls_text.append(prompt)
        return self.text_responses.pop(0)


# Retry ladder per the spec §1.3 decision #8:
#   primary attempts 1..3 with backoff 0.5s, 1s, 2s
#   fallback attempts 1..3 with backoff 0.5s, 1s, 2s
_BACKOFFS = (0.5, 1.0, 2.0)


@dataclass
class GroqLLMClient:
    """Groq HTTP client with retry-and-fallback policy."""

    api_key: str
    primary: str
    fallback: str

    # ---- overridable seams for tests ----
    async def _raw_call(self, *, model: str, prompt: str, json_mode: bool) -> str:
        # Real implementation deferred to inline import so tests can monkeypatch.
        from groq import AsyncGroq  # type: ignore

        client = AsyncGroq(api_key=self.api_key)
        kwargs: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def _is_rate_limit(self, exc: Exception) -> bool:
        # Groq SDK raises groq.APIStatusError with .status_code on 429
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return status == 429

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

# > **Shipped deviation (Phase D doc update, 2026-06-28):** the actual
# > `_run_with_ladder` wraps the call with `inspect.isawaitable(self._sleep(...))`
# > so tests can monkeypatch `_sleep` to a sync lambda. The retry loop also skips
# > the sleep on the final attempt (avoids 2s wasted tail latency before raising).
# > Phase D Tier 4 backlog flags the `inspect.isawaitable` shim as cosmetic cleanup
# > to revisit if `_sleep` is ever made uniformly async in tests.

    # ---- public API ----
    async def complete_json(self, prompt: str) -> dict:
        raw = await self._run_with_ladder(prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMUnavailable(f"malformed JSON from LLM: {e}") from e

    async def complete_text(self, prompt: str) -> str:
        return await self._run_with_ladder(prompt, json_mode=False)

    async def _run_with_ladder(self, prompt: str, *, json_mode: bool) -> str:
        for model in (self.primary, self.fallback):
            for backoff in _BACKOFFS:
                try:
                    return await self._raw_call(model=model, prompt=prompt, json_mode=json_mode)
                except Exception as e:  # noqa: BLE001
                    if not self._is_rate_limit(e):
                        # Non-rate-limit: fail fast, do not try fallback model
                        raise LLMUnavailable(f"LLM call failed (non-429): {e}") from e
                    await self._sleep(backoff)
        raise LLMUnavailable("all primary and fallback attempts rate-limited")


@lru_cache
def get_default_llm() -> LLMClient:
    settings = get_settings()
    return GroqLLMClient(
        api_key=settings.groq_api_key,
        primary=settings.llm_primary_model,
        fallback=settings.llm_fallback_model,
    )
```

- [ ] **Step 5: Run tests**

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/answer_generation/__init__.py backend/app/services/answer_generation/llm_client.py backend/tests/test_llm_client.py
git commit -m "feat(llm): LLMClient Protocol + FakeLLMClient + GroqLLMClient with retry/fallback"
```

---

## Task 5: Conflict prefilter

**Files:**
- Create: `backend/app/services/conflict_detection/__init__.py` (empty marker)
- Create: `backend/app/services/conflict_detection/prefilter.py`
- Create: `backend/tests/test_conflict_prefilter.py`

- [ ] **Step 1: Create the package marker**

Create `backend/app/services/conflict_detection/__init__.py`:

```python
"""Conflict-detection service — populated in later tasks."""
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_conflict_prefilter.py`:

```python
from __future__ import annotations

import datetime as dt
import uuid

from app.domain.chunk import RetrievalResult
from app.services.conflict_detection.prefilter import (
    MAX_PAIRS_PER_QUERY,
    build_candidate_pairs,
)


def _r(*, dept: str, lineage: uuid.UUID, ents: tuple[str, ...], rank: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="t",
        classification="public",
        department=dept,
        effective_date=dt.date(2024, 1, 1),
        snippet="x",
        score=0.0,
        rank=rank,
    )._replace_with_lineage_and_entities(lineage_id=lineage, entities=ents)
```

Wait — `RetrievalResult` doesn't currently carry `lineage_id` or `entities`. The prefilter needs both. Two options:

1. Add `lineage_id` and `entities` to `RetrievalResult` (modify Phase B domain).
2. Have the orchestrator look them up from chunk rows when building pairs.

Option 1 is cleaner — they're cheap, denormalized, already on `chunks` rows, and `RetrievalResult` is the natural carrier. Continue from there.

Replace the test fixture and continue. Edit `backend/app/domain/chunk.py` to add the two fields (this is necessary for the prefilter to work).

Edit `backend/app/domain/chunk.py`:

```python
@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    score: float
    rank: int
    lineage_id: uuid.UUID
    entities: tuple[str, ...]
```

- [ ] **Step 3: Update Phase B retrieval to populate the new fields**

The retrieval `ChunkHit`/`ChunkRepository` must surface `lineage_id` and `entities` so the orchestrator can build a complete `RetrievalResult`. Open `backend/app/repositories/chunk_repository.py` and:

1. Add `lineage_id: uuid.UUID` and `entities: tuple[str, ...]` to the `ChunkHit` dataclass.
2. In the SELECT statements of `bm25_topn` and `vector_topn`, add `c.lineage_id` and `c.entities` to the columns.
3. In the dataclass-construction lines, pass them through.

Open `backend/app/services/retrieval/__init__.py` and pass them when constructing `RetrievalResult`:

```python
        results.append(
            RetrievalResult(
                chunk_id=h.chunk_id, document_id=h.document_id,
                document_title=h.document_title, classification=h.classification,
                department=h.department, effective_date=h.effective_date,
                snippet=h.snippet, score=score, rank=fused_rank,
                lineage_id=h.lineage_id, entities=tuple(h.entities or ()),
            )
        )
```

Phase B tests already construct `RetrievalResult` in places — update them to pass `lineage_id=uuid.uuid4()` and `entities=()` to keep them green. Search for `RetrievalResult(` in the tests folder and add the two kwargs where missing.

Run after this change:

```powershell
python -m pytest -v
```

Expected: all existing tests still pass.

- [ ] **Step 4: Write the prefilter tests (rewritten)**

Replace `backend/tests/test_conflict_prefilter.py` with the corrected version:

```python
from __future__ import annotations

import datetime as dt
import uuid

from app.domain.chunk import RetrievalResult
from app.services.conflict_detection.prefilter import (
    MAX_PAIRS_PER_QUERY,
    build_candidate_pairs,
)


def _r(
    *,
    dept: str,
    lineage: uuid.UUID,
    ents: tuple[str, ...],
    rank: int,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="t",
        classification="public",
        department=dept,
        effective_date=dt.date(2024, 1, 1),
        snippet="x",
        score=0.0,
        rank=rank,
        lineage_id=lineage,
        entities=ents,
    )


def test_lineage_pair_is_a_candidate():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, ents=(), rank=1)
    b = _r(dept="hr", lineage=L, ents=(), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1
    assert pairs[0].canonical_key() == tuple(sorted((a.chunk_id, b.chunk_id)))


def test_same_dept_two_overlapping_entities_is_a_candidate():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "cadence", "policy"), rank=1)
    b = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "cadence", "other"), rank=3)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1


def test_same_dept_one_overlapping_entity_is_not():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit",), rank=1)
    b = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "other"), rank=3)
    pairs = build_candidate_pairs([a, b])
    assert pairs == []


def test_cross_dept_three_overlapping_entities_is_a_candidate():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "incident", "review"), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), ents=("audit", "incident", "review"), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert len(pairs) == 1


def test_cross_dept_two_overlapping_entities_is_not():
    a = _r(dept="hr", lineage=uuid.uuid4(), ents=("audit", "incident"), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), ents=("audit", "incident"), rank=2)
    pairs = build_candidate_pairs([a, b])
    assert pairs == []


def test_caps_to_max_pairs_per_query():
    L = uuid.uuid4()
    chunks = [_r(dept="hr", lineage=L, ents=(), rank=i + 1) for i in range(6)]
    # All same lineage -> C(6,2)=15 candidate pairs raw
    pairs = build_candidate_pairs(chunks)
    assert len(pairs) == MAX_PAIRS_PER_QUERY


def test_pairs_sorted_by_rank_sum_ascending():
    L = uuid.uuid4()
    c1 = _r(dept="hr", lineage=L, ents=(), rank=1)
    c2 = _r(dept="hr", lineage=L, ents=(), rank=2)
    c3 = _r(dept="hr", lineage=L, ents=(), rank=5)
    pairs = build_candidate_pairs([c1, c2, c3])
    assert pairs[0].rank_sum() <= pairs[1].rank_sum() <= pairs[2].rank_sum()


def test_pair_key_orderless_dedup():
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, ents=(), rank=1)
    b = _r(dept="hr", lineage=L, ents=(), rank=2)
    pairs = build_candidate_pairs([a, b, b, a])  # synthetic dup input
    # Same conceptual pair must not appear twice
    keys = {p.canonical_key() for p in pairs}
    assert len(keys) == len(pairs)
```

- [ ] **Step 5: Run tests to verify failure**

```powershell
python -m pytest tests/test_conflict_prefilter.py -v
```

Expected: ImportError on prefilter.

- [ ] **Step 6: Implement `prefilter.py`**

Create `backend/app/services/conflict_detection/prefilter.py`:

```python
from __future__ import annotations

from itertools import combinations

from app.domain.chunk import RetrievalResult
from app.domain.conflict import ConflictPair

MAX_PAIRS_PER_QUERY = 4
SAME_DEPT_ENTITY_THRESHOLD = 2
CROSS_DEPT_ENTITY_THRESHOLD = 3


def _is_candidate(a: RetrievalResult, b: RetrievalResult) -> bool:
    if a.chunk_id == b.chunk_id:
        return False
    if a.lineage_id == b.lineage_id:
        return True
    overlap = len(set(a.entities) & set(b.entities))
    if a.department == b.department:
        return overlap >= SAME_DEPT_ENTITY_THRESHOLD
    return overlap >= CROSS_DEPT_ENTITY_THRESHOLD


def build_candidate_pairs(results: list[RetrievalResult]) -> list[ConflictPair]:
    candidates: dict[tuple, ConflictPair] = {}
    for a, b in combinations(results, 2):
        if not _is_candidate(a, b):
            continue
        pair = ConflictPair(
            chunk_a_id=a.chunk_id,
            chunk_b_id=b.chunk_id,
            a_rank=a.rank,
            b_rank=b.rank,
        )
        # Dedup on canonical key; keep the first occurrence
        candidates.setdefault(pair.canonical_key(), pair)
    ranked = sorted(candidates.values(), key=lambda p: p.rank_sum())
    return ranked[:MAX_PAIRS_PER_QUERY]
```

- [ ] **Step 7: Run tests**

```powershell
python -m pytest tests/test_conflict_prefilter.py -v
```

Expected: 8 passed.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/domain/chunk.py backend/app/repositories/chunk_repository.py backend/app/services/retrieval/__init__.py backend/app/services/conflict_detection/__init__.py backend/app/services/conflict_detection/prefilter.py backend/tests/test_conflict_prefilter.py backend/tests
git commit -m "feat(conflict): prefilter with lineage + entity-overlap thresholds; surface lineage/entities on RetrievalResult"
```

Note: include any test files you had to touch in step 3 to keep Phase B green.

---

## Task 6: Conflict judge + LRU cache

**Files:**
- Create: `backend/app/services/conflict_detection/prompts.py`
- Create: `backend/app/services/conflict_detection/judge.py`
- Create: `backend/tests/test_conflict_judge.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_conflict_judge.py`:

```python
from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.domain.conflict import ConflictPair
from app.services.answer_generation.llm_client import FakeLLMClient
from app.services.conflict_detection.judge import judge_pair, _judge_cache_clear


def _r(rank: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=f"Doc{rank}",
        classification="public",
        department="hr",
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text {rank}",
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_conflict_when_llm_says_so():
    _judge_cache_clear()
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True,
        "subject": "audit cadence",
        "position_a": "weekly",
        "position_b": "monthly",
    }])
    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert result is not None
    assert result.subject == "audit cadence"
    assert result.position_a.text == "weekly"
    assert result.position_b.text == "monthly"


@pytest.mark.asyncio
async def test_returns_none_when_llm_says_no_conflict():
    _judge_cache_clear()
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": False, "subject": "", "position_a": "", "position_b": "",
    }])
    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_skips_llm_for_same_pair():
    _judge_cache_clear()
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, a.rank, b.rank)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "s", "position_a": "x", "position_b": "y",
    }])
    out1 = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    out2 = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=fake)
    assert out1 is not None and out2 is not None
    assert len(fake.calls_json) == 1  # cached on second call


@pytest.mark.asyncio
async def test_cache_key_is_orderless():
    _judge_cache_clear()
    a, b = _r(1), _r(2)
    pair_ab = ConflictPair(a.chunk_id, b.chunk_id, 1, 2)
    pair_ba = ConflictPair(b.chunk_id, a.chunk_id, 2, 1)
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "s", "position_a": "x", "position_b": "y",
    }])
    await judge_pair(pair=pair_ab, chunk_a=a, chunk_b=b, llm=fake)
    await judge_pair(pair=pair_ba, chunk_a=b, chunk_b=a, llm=fake)
    assert len(fake.calls_json) == 1


@pytest.mark.asyncio
async def test_returns_none_on_llm_unavailable():
    from app.services.answer_generation.llm_client import LLMUnavailable

    _judge_cache_clear()
    a, b = _r(1), _r(2)
    pair = ConflictPair(a.chunk_id, b.chunk_id, 1, 2)

    class _RaisingLLM:
        async def complete_json(self, _p: str) -> dict:
            raise LLMUnavailable("boom")
        async def complete_text(self, _p: str) -> str:
            raise LLMUnavailable("boom")

    result = await judge_pair(pair=pair, chunk_a=a, chunk_b=b, llm=_RaisingLLM())
    assert result is None
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_conflict_judge.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement prompts**

Create `backend/app/services/conflict_detection/prompts.py`:

```python
from __future__ import annotations

JUDGE_PROMPT = """You are a conflict detector. Two passages from internal documents appear below.
Decide whether they make INCOMPATIBLE claims about the SAME subject.

A passage that adds detail to another, or discusses a different topic, is NOT a conflict.
Only flag genuine contradictions on the same subject.

PASSAGE_A - title: "{a_title}" - effective: {a_date} - dept: {a_dept}
{a_text}

PASSAGE_B - title: "{b_title}" - effective: {b_date} - dept: {b_dept}
{b_text}

Reply ONLY in JSON matching this schema:
{{
  "conflict": true | false,
  "subject": "short noun phrase",
  "position_a": "one-sentence summary of A's claim on the subject",
  "position_b": "one-sentence summary of B's claim on the subject"
}}"""


def render_judge_prompt(*, a_title: str, a_date: str, a_dept: str, a_text: str,
                        b_title: str, b_date: str, b_dept: str, b_text: str) -> str:
    return JUDGE_PROMPT.format(
        a_title=a_title, a_date=a_date, a_dept=a_dept, a_text=a_text,
        b_title=b_title, b_date=b_date, b_dept=b_dept, b_text=b_text,
    )
```

- [ ] **Step 4: Implement judge with cache**

Create `backend/app/services/conflict_detection/judge.py`:

```python
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, ConflictPair, Position
from app.services.answer_generation.llm_client import LLMClient, LLMUnavailable
from app.services.conflict_detection.prompts import render_judge_prompt

log = logging.getLogger(__name__)

# Module-global cache: canonical pair key -> Conflict | None.
# functools.lru_cache doesn't fit async; we hand-roll a simple bounded dict.
_CACHE_CAPACITY = 256
_cache: "dict[tuple[uuid.UUID, uuid.UUID], Conflict | None]" = {}
_cache_order: list[tuple[uuid.UUID, uuid.UUID]] = []


def _judge_cache_clear() -> None:
    _cache.clear()
    _cache_order.clear()


def _cache_get(key: tuple[uuid.UUID, uuid.UUID]) -> tuple[bool, Conflict | None]:
    if key in _cache:
        return True, _cache[key]
    return False, None


def _cache_put(key: tuple[uuid.UUID, uuid.UUID], value: Conflict | None) -> None:
    if key in _cache:
        return
    _cache[key] = value
    _cache_order.append(key)
    while len(_cache_order) > _CACHE_CAPACITY:
        oldest = _cache_order.pop(0)
        _cache.pop(oldest, None)


def _build_conflict(payload: dict[str, Any], chunk_a: RetrievalResult, chunk_b: RetrievalResult) -> Conflict | None:
    if not payload.get("conflict"):
        return None
    return Conflict(
        subject=str(payload.get("subject", "")).strip() or "Unspecified",
        position_a=Position(marker=0, chunk_id=chunk_a.chunk_id, text=str(payload.get("position_a", "")).strip()),
        position_b=Position(marker=0, chunk_id=chunk_b.chunk_id, text=str(payload.get("position_b", "")).strip()),
    )


async def judge_pair(
    *,
    pair: ConflictPair,
    chunk_a: RetrievalResult,
    chunk_b: RetrievalResult,
    llm: LLMClient,
) -> Conflict | None:
    key = pair.canonical_key()
    hit, cached = _cache_get(key)
    if hit:
        return cached

    prompt = render_judge_prompt(
        a_title=chunk_a.document_title, a_date=chunk_a.effective_date.isoformat(),
        a_dept=chunk_a.department, a_text=chunk_a.snippet,
        b_title=chunk_b.document_title, b_date=chunk_b.effective_date.isoformat(),
        b_dept=chunk_b.department, b_text=chunk_b.snippet,
    )
    try:
        payload = await llm.complete_json(prompt)
    except LLMUnavailable as e:
        log.warning("judge LLM unavailable for pair=%s err=%s", key, e)
        # Do not cache transient failures
        return None

    conflict = _build_conflict(payload, chunk_a, chunk_b)
    _cache_put(key, conflict)
    return conflict
```

Note: positions are returned with `marker=0` here; the orchestrator assigns the real marker once it knows where each chunk lives in the final citation list. This separation keeps the judge unaware of citation numbering.

- [ ] **Step 5: Run tests**

```powershell
python -m pytest tests/test_conflict_judge.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/conflict_detection/prompts.py backend/app/services/conflict_detection/judge.py backend/tests/test_conflict_judge.py
git commit -m "feat(conflict): LLM-as-judge with orderless pair cache"
```

---

## Task 7: `detect_conflicts` orchestrator

**Files:**
- Modify: `backend/app/services/conflict_detection/__init__.py`
- Create: `backend/tests/test_conflict_detection.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_conflict_detection.py`:

```python
from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.services.answer_generation.llm_client import FakeLLMClient
from app.services.conflict_detection import detect_conflicts
from app.services.conflict_detection.judge import _judge_cache_clear


def _r(*, dept: str, lineage: uuid.UUID, rank: int, title: str = "t") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department=dept,
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text {rank}",
        score=0.0,
        rank=rank,
        lineage_id=lineage,
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_empty_when_no_pairs():
    _judge_cache_clear()
    a = _r(dept="hr", lineage=uuid.uuid4(), rank=1)
    b = _r(dept="security", lineage=uuid.uuid4(), rank=2)
    conflicts = await detect_conflicts(results=[a, b], llm=FakeLLMClient())
    assert conflicts == []


@pytest.mark.asyncio
async def test_detects_lineage_pair():
    _judge_cache_clear()
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, rank=1, title="Handbook 2019")
    b = _r(dept="hr", lineage=L, rank=2, title="Supplement 2023")
    fake = FakeLLMClient(json_responses=[{
        "conflict": True, "subject": "insignia",
        "position_a": "no insignia off-base",
        "position_b": "may retain unit insignia",
    }])
    conflicts = await detect_conflicts(results=[a, b], llm=fake)
    assert len(conflicts) == 1
    assert conflicts[0].subject == "insignia"


@pytest.mark.asyncio
async def test_filters_out_no_conflict_judgments():
    _judge_cache_clear()
    L = uuid.uuid4()
    a = _r(dept="hr", lineage=L, rank=1)
    b = _r(dept="hr", lineage=L, rank=2)
    fake = FakeLLMClient(json_responses=[{
        "conflict": False, "subject": "", "position_a": "", "position_b": "",
    }])
    conflicts = await detect_conflicts(results=[a, b], llm=fake)
    assert conflicts == []
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_conflict_detection.py -v
```

Expected: ImportError on `detect_conflicts`.

- [ ] **Step 3: Implement orchestrator**

Edit `backend/app/services/conflict_detection/__init__.py`:

```python
from __future__ import annotations

import asyncio

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict
from app.services.answer_generation.llm_client import LLMClient
from app.services.conflict_detection.judge import judge_pair
from app.services.conflict_detection.prefilter import build_candidate_pairs


async def detect_conflicts(
    *, results: list[RetrievalResult], llm: LLMClient
) -> list[Conflict]:
    pairs = build_candidate_pairs(results)
    if not pairs:
        return []
    by_id = {r.chunk_id: r for r in results}
    coros = [
        judge_pair(pair=p, chunk_a=by_id[p.chunk_a_id], chunk_b=by_id[p.chunk_b_id], llm=llm)
        for p in pairs
    ]
    judged = await asyncio.gather(*coros)
    return [c for c in judged if c is not None]
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/test_conflict_detection.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/conflict_detection/__init__.py backend/tests/test_conflict_detection.py
git commit -m "feat(conflict): detect_conflicts orchestrator over prefilter + judge"
```

---

## Task 8: Answer-generation prompts + context rendering

**Files:**
- Create: `backend/app/services/answer_generation/prompts.py`
- Create: `backend/tests/test_answer_prompts.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_answer_prompts.py`:

```python
from __future__ import annotations

import datetime as dt
import uuid

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    REFINE_TEMPLATE_STR,
    render_context_block,
    render_conflicts_block,
)


def _r(rank: int, title: str, dept: str, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department=dept,
        effective_date=dt.date(2023, 1, 1),
        snippet=text,
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


def test_context_block_numbers_chunks_starting_at_one():
    chunks = [_r(1, "A", "hr", "text-a"), _r(2, "B", "security", "text-b")]
    out = render_context_block(chunks)
    assert "[1]" in out and "[2]" in out
    assert "text-a" in out and "text-b" in out
    assert "doc: \"A\"" in out and "doc: \"B\"" in out


def test_conflicts_block_uses_provided_markers():
    chunks = [_r(1, "A", "hr", "ta"), _r(2, "B", "hr", "tb")]
    c = Conflict(
        subject="dress code",
        position_a=Position(marker=1, chunk_id=chunks[0].chunk_id, text="no insignia"),
        position_b=Position(marker=2, chunk_id=chunks[1].chunk_id, text="may retain"),
    )
    out = render_conflicts_block([c])
    assert "Subject: dress code" in out
    assert "[1] states: no insignia" in out
    assert "[2] states: may retain" in out


def test_conflicts_block_empty_when_no_conflicts():
    assert render_conflicts_block([]) == ""


def test_answer_template_contains_required_markers():
    # Sanity: template surfaces query_str + context_str + conflicts_str placeholders
    assert "{context_str}" in ANSWER_TEMPLATE_STR
    assert "{query_str}" in ANSWER_TEMPLATE_STR
    assert "{conflicts_str}" in ANSWER_TEMPLATE_STR
    assert "[1]" in ANSWER_TEMPLATE_STR  # example shape


def test_refine_template_preserves_markers_instruction():
    assert "{query_str}" in REFINE_TEMPLATE_STR
    assert "preserve" in REFINE_TEMPLATE_STR.lower() or "keep" in REFINE_TEMPLATE_STR.lower()
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_answer_prompts.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement prompts module**

Create `backend/app/services/answer_generation/prompts.py`:

```python
from __future__ import annotations

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict


ANSWER_TEMPLATE_STR = """You are HOLOCRON, an enterprise knowledge assistant for the Imperial archives.
Answer the user's question using ONLY the numbered context blocks below.

Rules:
- Cite every claim with inline markers like [1], [2]. A claim may have multiple markers.
- Do NOT use information not present in the context.
- If the context is insufficient to answer, say so explicitly.
- When the CONFLICTS section is non-empty, acknowledge the disagreement with phrasing like:
  "Sources disagree: [n] states X; [m] states Y."
- Be concise. 3 to 5 sentences for typical questions.

CONTEXT:
{context_str}

CONFLICTS:
{conflicts_str}

QUESTION: {query_str}

ANSWER:"""


REFINE_TEMPLATE_STR = """An initial answer exists for the question.

Existing answer:
{existing_answer}

New context to consider:
{context_msg}

Refine the existing answer to incorporate the new context if relevant. Preserve all existing [n] citation markers; add new ones only for newly cited content. Do not introduce claims absent from the context. If the new context is irrelevant, return the existing answer unchanged.

QUESTION: {query_str}

REFINED ANSWER:"""


def render_context_block(chunks: list[RetrievalResult]) -> str:
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] (clearance: {c.classification}, dept: {c.department}, "
            f"effective: {c.effective_date.isoformat()}, doc: \"{c.document_title}\")\n"
            f"{c.snippet}"
        )
    return "\n\n".join(parts)


def render_conflicts_block(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return ""
    parts: list[str] = []
    for c in conflicts:
        parts.append(
            f"- Subject: {c.subject}\n"
            f"  [{c.position_a.marker}] states: {c.position_a.text}\n"
            f"  [{c.position_b.marker}] states: {c.position_b.text}"
        )
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/test_answer_prompts.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/answer_generation/prompts.py backend/tests/test_answer_prompts.py
git commit -m "feat(answer): prompt templates + context/conflicts block rendering"
```

---

## Task 9: Citation parsing

**Files:**
- Create: `backend/app/services/answer_generation/citations.py`
- Create: `backend/tests/test_citations.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_citations.py`:

```python
from __future__ import annotations

import uuid

from app.services.answer_generation.citations import parse_citation_markers


def test_finds_markers_in_text():
    text = "Foo [1] and bar [2], also [1] again."
    assert parse_citation_markers(text, total_chunks=3) == [1, 2]


def test_drops_out_of_range_markers():
    text = "Foo [1] bar [99]."
    assert parse_citation_markers(text, total_chunks=2) == [1]


def test_returns_empty_for_no_markers():
    assert parse_citation_markers("nothing cited here", total_chunks=5) == []


def test_returns_empty_for_zero_chunks():
    assert parse_citation_markers("[1] [2]", total_chunks=0) == []
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_citations.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement citations**

Create `backend/app/services/answer_generation/citations.py`:

```python
from __future__ import annotations

import re

_MARKER_RE = re.compile(r"\[(\d+)\]")


def parse_citation_markers(text: str, *, total_chunks: int) -> list[int]:
    if total_chunks <= 0:
        return []
    found = sorted({int(m) for m in _MARKER_RE.findall(text)})
    return [i for i in found if 1 <= i <= total_chunks]
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/test_citations.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/answer_generation/citations.py backend/tests/test_citations.py
git commit -m "feat(answer): citation marker parser with out-of-range filter"
```

---

## Task 10: `generate_answer` service

**Files:**
- Modify: `backend/app/services/answer_generation/__init__.py`
- Create: `backend/tests/test_answer_generation.py`

The spec locks in **LlamaIndex `CompactAndRefine`**. Our `LLMClient` Protocol is the right seam for testing — it covers both judge and synthesizer call paths uniformly and applies our retry-and-fallback ladder. The implementation here uses `LLMClient.complete_text` directly, with the prompt assembled from the LlamaIndex-style `CompactAndRefine` template. At top-k=6 (~3K context tokens), a single compaction-and-fill produces the answer in one LLM call; the refine template stays available for the multi-batch case but is never exercised on the current corpus.

> **Note on "use LlamaIndex CompactAndRefine":** the spec accepts this implementation strategy in §4.5: *"Implementation choice (wrap the LlamaIndex Groq LLM with a retry decorator, or call our GroqLLMClient.complete_text from a thin custom synthesizer instead of LlamaIndex's, or any equivalent) is deferred to the implementation plan."* We pick the `LLMClient.complete_text` route — the prompt template literally is the LlamaIndex CompactAndRefine `text_qa_template` shape (rendered with our context + conflict blocks), so the canonical pattern is preserved at the prompt level. This keeps the retry policy in one place and tests deterministic.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_answer_generation.py`:

```python
from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import FakeLLMClient


def _r(rank: int, title: str = "t") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title=title,
        classification="public",
        department="hr",
        effective_date=dt.date(2024, 1, 1),
        snippet=f"text-{rank}",
        score=0.0,
        rank=rank,
        lineage_id=uuid.uuid4(),
        entities=(),
    )


@pytest.mark.asyncio
async def test_returns_answer_and_cited_chunk_ids():
    chunks = [_r(1, "A"), _r(2, "B"), _r(3, "C")]
    fake = FakeLLMClient(text_responses=["Answer references [1] and [3]."])
    out = await generate_answer(query="what?", chunks=chunks, conflicts=[], llm=fake)
    assert "[1]" in out.text and "[3]" in out.text
    assert out.cited_chunk_ids == [chunks[0].chunk_id, chunks[2].chunk_id]


@pytest.mark.asyncio
async def test_drops_out_of_range_markers():
    chunks = [_r(1, "A"), _r(2, "B")]
    fake = FakeLLMClient(text_responses=["Cited [1] and bogus [99]."])
    out = await generate_answer(query="q", chunks=chunks, conflicts=[], llm=fake)
    assert out.cited_chunk_ids == [chunks[0].chunk_id]


@pytest.mark.asyncio
async def test_assigns_conflict_markers_from_chunk_order():
    chunks = [_r(1, "A"), _r(2, "B")]
    # Pre-judge phase emits marker=0; generate_answer must re-assign markers
    raw = Conflict(
        subject="dress code",
        position_a=Position(marker=0, chunk_id=chunks[0].chunk_id, text="A says"),
        position_b=Position(marker=0, chunk_id=chunks[1].chunk_id, text="B says"),
    )
    fake = FakeLLMClient(text_responses=["Discussed [1] vs [2]."])
    out = await generate_answer(query="q", chunks=chunks, conflicts=[raw], llm=fake)
    assert out.conflicts[0].position_a.marker == 1
    assert out.conflicts[0].position_b.marker == 2


@pytest.mark.asyncio
async def test_empty_chunks_does_not_call_llm():
    fake = FakeLLMClient(text_responses=[])
    out = await generate_answer(query="q", chunks=[], conflicts=[], llm=fake)
    assert out.text == "I cannot answer this question with the available context."
    assert out.cited_chunk_ids == []
    assert out.conflicts == []
    assert fake.calls_text == []
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_answer_generation.py -v
```

Expected: ImportError on `generate_answer`.

- [ ] **Step 3: Implement `generate_answer`**

Replace `backend/app/services/answer_generation/__init__.py` with:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.chunk import RetrievalResult
from app.domain.conflict import Conflict, Position
from app.services.answer_generation.citations import parse_citation_markers
from app.services.answer_generation.llm_client import LLMClient
from app.services.answer_generation.prompts import (
    ANSWER_TEMPLATE_STR,
    render_context_block,
    render_conflicts_block,
)


@dataclass(frozen=True)
class AnswerWithCitations:
    text: str
    cited_chunk_ids: list[uuid.UUID]
    conflicts: list[Conflict]


_FALLBACK_ANSWER = "I cannot answer this question with the available context."


def _assign_conflict_markers(
    conflicts: list[Conflict], chunks: list[RetrievalResult]
) -> list[Conflict]:
    """Re-emit Conflicts with position markers set to the 1-based index of each
    chunk in the final citation list."""
    by_id_idx = {c.chunk_id: i + 1 for i, c in enumerate(chunks)}
    out: list[Conflict] = []
    for c in conflicts:
        m_a = by_id_idx.get(c.position_a.chunk_id, 0)
        m_b = by_id_idx.get(c.position_b.chunk_id, 0)
        out.append(
            Conflict(
                subject=c.subject,
                position_a=Position(marker=m_a, chunk_id=c.position_a.chunk_id, text=c.position_a.text),
                position_b=Position(marker=m_b, chunk_id=c.position_b.chunk_id, text=c.position_b.text),
            )
        )
    return out


async def generate_answer(
    *,
    query: str,
    chunks: list[RetrievalResult],
    conflicts: list[Conflict],
    llm: LLMClient,
) -> AnswerWithCitations:
    if not chunks:
        return AnswerWithCitations(text=_FALLBACK_ANSWER, cited_chunk_ids=[], conflicts=[])

    conflicts_with_markers = _assign_conflict_markers(conflicts, chunks)
    prompt = ANSWER_TEMPLATE_STR.format(
        context_str=render_context_block(chunks),
        conflicts_str=render_conflicts_block(conflicts_with_markers) or "(none)",
        query_str=query,
    )
    text = await llm.complete_text(prompt)
    cited_indices = parse_citation_markers(text, total_chunks=len(chunks))
    cited_chunk_ids = [chunks[i - 1].chunk_id for i in cited_indices]
    return AnswerWithCitations(
        text=text, cited_chunk_ids=cited_chunk_ids, conflicts=conflicts_with_markers
    )
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/test_answer_generation.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/answer_generation/__init__.py backend/tests/test_answer_generation.py
git commit -m "feat(answer): generate_answer with citation parsing and conflict-marker assignment"
```

---

## Task 11: AuditRepository.insert_response

**Files:**
- Modify: `backend/app/repositories/audit_repository.py`
- Create: `backend/tests/test_audit_response.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_audit_response.py`:

```python
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent, Tenant
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_response_writes_row(db_session, empire_tenant: Tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    await repo.insert_response(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        response_text="The answer.",
        conflicts_found={"count": 1, "subjects": ["dress code"]},
        latency_ms=412,
    )
    await db_session.flush()
    rows = (await db_session.execute(
        select(AuditEvent).where(AuditEvent.event_type == "response")
    )).scalars().all()
    assert len(rows) == 1
    r = rows[0]
    assert r.response_text == "The answer."
    assert r.conflicts_found == {"count": 1, "subjects": ["dress code"]}
    assert r.latency_ms == 412
```

- [ ] **Step 2: Run test to verify failure**

```powershell
python -m pytest tests/test_audit_response.py -v
```

Expected: AttributeError on `insert_response`.

- [ ] **Step 3: Add `insert_response`**

Edit `backend/app/repositories/audit_repository.py`. Append:

```python
    async def insert_response(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        response_text: str,
        conflicts_found: dict | None,
        latency_ms: int,
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="response",
                response_text=response_text,
                conflicts_found=conflicts_found,
                latency_ms=latency_ms,
            )
        )
```

- [ ] **Step 4: Run test**

```powershell
python -m pytest tests/test_audit_response.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/repositories/audit_repository.py backend/tests/test_audit_response.py
git commit -m "feat(audit): insert_response writer for chat-flow events"
```

---

## Task 12: API schemas for chat

**Files:**
- Modify: `backend/app/api/schemas.py`

- [ ] **Step 1: Add Pydantic schemas**

Append to `backend/app/api/schemas.py`:

```python
class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=10)


class AnswerOut(BaseModel):
    text: str
    cited_chunk_ids: list[uuid.UUID]


class CitationOut(BaseModel):
    marker: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str


class PositionOut(BaseModel):
    marker: int
    text: str


class ConflictOut(BaseModel):
    subject: str
    position_a: PositionOut
    position_b: PositionOut


class RefusalOut(BaseModel):
    reference_id: str
    withheld_count: int


class ChatResponse(BaseModel):
    query: str
    answer: AnswerOut
    citations: list[CitationOut]
    conflicts: list[ConflictOut]
    refusal: RefusalOut | None = None
```

- [ ] **Step 2: Verify still imports cleanly**

```powershell
python -c "from app.api.schemas import ChatRequest, ChatResponse; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/schemas.py
git commit -m "feat(api): chat request/response Pydantic schemas"
```

---

## Task 13: `POST /chat/ask` endpoint + wiring

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat_endpoint.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_chat_endpoint.py`. This follows the Phase A pattern (`tests/test_auth_api.py`): log in via `POST /auth/login` so the cookie is set on the httpx client, then call `/chat/ask`. Dependency overrides inject the FakeLLMClient and FakeEmbeddingProvider.

```python
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Tenant, User
from app.main import app
from app.services.answer_generation.llm_client import FakeLLMClient, get_default_llm
from app.services.conflict_detection.judge import _judge_cache_clear
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder


@pytest_asyncio.fixture
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[get_default_embedder] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[get_default_llm] = lambda: FakeLLMClient(
        text_responses=["Answer about [1] thing."],
        json_responses=[],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_executive(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="ex-proc",
        password_hash=hash_password("imperial-march"),
        role=Role.EXECUTIVE.value,
        max_clearance=ClearanceLevel.TOP_SECRET.value,
        departments=["procurement", "hr"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _login(client: AsyncClient, tenant_id, username, password) -> None:
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(tenant_id), "username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_chat_ask_returns_full_payload(client, empire_tenant, seeded_executive):
    _judge_cache_clear()
    await _login(client, empire_tenant.id, "ex-proc", "imperial-march")

    resp = await client.post("/chat/ask", json={"query": "anything", "top_k": 6})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["query"] == "anything"
    assert payload["answer"]["text"].startswith("Answer about")
    assert payload["conflicts"] == []
    assert "citations" in payload


@pytest.mark.asyncio
async def test_chat_ask_unauthenticated_is_401(client):
    resp = await client.post("/chat/ask", json={"query": "q"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_ask_rejects_empty_query(client, empire_tenant, seeded_executive):
    _judge_cache_clear()
    await _login(client, empire_tenant.id, "ex-proc", "imperial-march")
    resp = await client.post("/chat/ask", json={"query": "   "})
    # Either pydantic min_length=1 (422) or explicit 400 from the router check
    assert resp.status_code in (400, 422)
```

The Pydantic schema's `min_length=1` enforces non-empty at the body level, returning 422. The router's explicit `.strip()` check catches whitespace-only input and returns 400. Either is acceptable per the spec.

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_chat_endpoint.py -v
```

Expected: 404 (route not registered) or ImportError.

- [ ] **Step 3: Implement the router**

Create `backend/app/api/chat.py`:

```python
from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AnswerOut, ChatRequest, ChatResponse, CitationOut, ConflictOut,
    PositionOut, RefusalOut,
)
from app.core.clearance import ClearanceContext
from app.core.database import get_session
from app.core.tenant import get_tenant_context
from app.repositories.audit_repository import AuditRepository
from app.services.answer_generation import generate_answer
from app.services.answer_generation.llm_client import LLMClient, LLMUnavailable, get_default_llm
from app.services.conflict_detection import detect_conflicts
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder
from app.services.retrieval import search

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
async def post_ask(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
    tenant_ctx=Depends(get_tenant_context),
    embedder: EmbeddingProvider = Depends(get_default_embedder),
    llm: LLMClient = Depends(get_default_llm),
) -> ChatResponse:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")

    ctx = ClearanceContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        max_clearance=tenant_ctx.max_clearance,
        departments=tuple(tenant_ctx.departments),
    )

    t0 = perf_counter()
    search_resp = await search(
        session=session, ctx=ctx, embedder=embedder, query=body.query, top_k=body.top_k,
    )
    results = list(search_resp.results)

    conflicts = await detect_conflicts(results=results, llm=llm)

    try:
        answer = await generate_answer(
            query=body.query, chunks=results, conflicts=conflicts, llm=llm,
        )
    except LLMUnavailable as e:
        raise HTTPException(status_code=503, detail="LLM temporarily unavailable. Please retry.") from e

    latency_ms = int((perf_counter() - t0) * 1000)

    cited_set = set(answer.cited_chunk_ids)
    citations: list[CitationOut] = []
    for i, r in enumerate(results, start=1):
        if r.chunk_id not in cited_set:
            continue
        citations.append(
            CitationOut(
                marker=i, chunk_id=r.chunk_id, document_id=r.document_id,
                document_title=r.document_title, classification=r.classification,
                department=r.department, effective_date=r.effective_date, snippet=r.snippet,
            )
        )

    audit = AuditRepository(session)
    await audit.insert_response(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        response_text=answer.text,
        conflicts_found={
            "count": len(answer.conflicts),
            "subjects": [c.subject for c in answer.conflicts],
        },
        latency_ms=latency_ms,
    )
    await session.flush()

    return ChatResponse(
        query=body.query,
        answer=AnswerOut(text=answer.text, cited_chunk_ids=answer.cited_chunk_ids),
        citations=citations,
        conflicts=[
            ConflictOut(
                subject=c.subject,
                position_a=PositionOut(marker=c.position_a.marker, text=c.position_a.text),
                position_b=PositionOut(marker=c.position_b.marker, text=c.position_b.text),
            )
            for c in answer.conflicts
        ],
        refusal=(
            RefusalOut(
                reference_id=search_resp.refusal.reference_id,
                withheld_count=search_resp.refusal.withheld_count,
            )
            if search_resp.refusal else None
        ),
    )
```

- [ ] **Step 4: Register router**

Edit `backend/app/main.py`. Add:

```python
from app.api.chat import router as chat_router
```

and below the other router includes:

```python
app.include_router(chat_router)
```

- [ ] **Step 5: Run tests**

```powershell
python -m pytest tests/test_chat_endpoint.py -v
```

Expected: 3 passed. If the auth-token helper symbol differs, fix the test to use whatever Phase A uses (e.g. log in via `POST /auth/login` first).

- [ ] **Step 6: Run full backend suite**

```powershell
python -m pytest -v
```

Expected: ~104 passing, 2-3 deselected (slow).

- [ ] **Step 7: Commit**

```powershell
git add backend/app/api/chat.py backend/app/main.py backend/tests/test_chat_endpoint.py
git commit -m "feat(api): POST /chat/ask orchestrating retrieval + conflicts + answer"
```

---

## Task 14: Frontend types + chat-api client

**Files:**
- Create: `frontend/lib/types/chat.ts`
- Create: `frontend/lib/chat-api.ts`
- Create: `frontend/lib/clearance-color.ts`

- [ ] **Step 1: Create types**

Create `frontend/lib/types/chat.ts`:

```ts
export type Clearance = 'public' | 'restricted' | 'secret' | 'top_secret';

export interface AnswerOut {
  text: string;
  cited_chunk_ids: string[];
}

export interface CitationOut {
  marker: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  classification: Clearance;
  department: string;
  effective_date: string;
  snippet: string;
}

export interface PositionOut {
  marker: number;
  text: string;
}

export interface ConflictOut {
  subject: string;
  position_a: PositionOut;
  position_b: PositionOut;
}

export interface RefusalOut {
  reference_id: string;
  withheld_count: number;
}

export interface ChatResponse {
  query: string;
  answer: AnswerOut;
  citations: CitationOut[];
  conflicts: ConflictOut[];
  refusal: RefusalOut | null;
}
```

- [ ] **Step 2: Create API client**

Create `frontend/lib/chat-api.ts`:

```ts
import { ChatResponse } from "@/lib/types/chat";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class LLMUnavailableError extends Error {}

export async function postChatAsk(query: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat/ask`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: 6 }),
  });
  if (res.status === 401) {
    throw new Error("unauthenticated");
  }
  if (res.status === 503) {
    throw new LLMUnavailableError("LLM temporarily unavailable. Please retry.");
  }
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
```

- [ ] **Step 3: Create clearance color helper**

Create `frontend/lib/clearance-color.ts`:

```ts
import { Clearance } from "@/lib/types/chat";

export function clearanceBadgeClasses(c: Clearance): string {
  switch (c) {
    case "public":
      return "bg-green-100 text-green-800 border-green-300";
    case "restricted":
      return "bg-amber-100 text-amber-800 border-amber-300";
    case "secret":
      return "bg-red-100 text-red-800 border-red-300";
    case "top_secret":
      return "bg-red-900 text-red-50 border-red-950";
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
```

- [ ] **Step 4: Verify Next typechecks**

```powershell
cd ..\frontend
pnpm exec tsc --noEmit
cd ..\backend
```

Expected: no errors.

- [ ] **Step 5: Commit**

```powershell
git add frontend/lib/types/chat.ts frontend/lib/chat-api.ts frontend/lib/clearance-color.ts
git commit -m "feat(chat-fe): TypeScript types, fetch client, clearance color helper"
```

---

## Task 15: Frontend small components — `ClearanceBadge`, `CitationCard`, `ConflictCard`, `RefusalNote`

**Files:**
- Create: `frontend/components/ClearanceBadge.tsx`
- Create: `frontend/app/chat/components/CitationCard.tsx`
- Create: `frontend/app/chat/components/ConflictCard.tsx`
- Create: `frontend/app/chat/components/RefusalNote.tsx`

- [ ] **Step 1: `ClearanceBadge`**

Create `frontend/components/ClearanceBadge.tsx`:

```tsx
import { clearanceBadgeClasses, clearanceLabel } from "@/lib/clearance-color";
import { Clearance } from "@/lib/types/chat";

export function ClearanceBadge({ classification }: { classification: Clearance }) {
  return (
    <span
      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold border ${clearanceBadgeClasses(classification)}`}
    >
      {clearanceLabel(classification)}
    </span>
  );
}
```

- [ ] **Step 2: `CitationCard`**

Create `frontend/app/chat/components/CitationCard.tsx`:

```tsx
import { ClearanceBadge } from "@/components/ClearanceBadge";
import { CitationOut } from "@/lib/types/chat";

export function CitationCard({ citation }: { citation: CitationOut }) {
  return (
    <div
      id={`cite-${citation.marker}`}
      className="p-3 border border-slate-200 rounded-lg bg-white"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-[11px] font-semibold">
          [{citation.marker}]
        </span>
        <ClearanceBadge classification={citation.classification} />
        <span className="text-[10px] text-slate-500">
          {citation.department} · {citation.effective_date}
        </span>
      </div>
      <div className="text-xs font-semibold mb-1">{citation.document_title}</div>
      <div className="text-[11px] text-slate-600 leading-snug">{citation.snippet}</div>
    </div>
  );
}
```

- [ ] **Step 3: `ConflictCard`**

Create `frontend/app/chat/components/ConflictCard.tsx`:

```tsx
import { ConflictOut } from "@/lib/types/chat";

export function ConflictCard({ conflict }: { conflict: ConflictOut }) {
  return (
    <div className="border border-red-200 rounded-lg bg-red-50 overflow-hidden">
      <div className="px-3 py-2 bg-red-100 text-[12px] font-semibold text-red-900">
        Subject: {conflict.subject}
      </div>
      <div className="grid grid-cols-2 gap-px bg-red-200">
        <a
          href={`#cite-${conflict.position_a.marker}`}
          className="block p-3 bg-white text-[11px] hover:bg-slate-50"
        >
          <div className="font-semibold mb-1">[{conflict.position_a.marker}]</div>
          <div className="text-slate-600">{conflict.position_a.text}</div>
        </a>
        <a
          href={`#cite-${conflict.position_b.marker}`}
          className="block p-3 bg-white text-[11px] hover:bg-slate-50"
        >
          <div className="font-semibold mb-1">[{conflict.position_b.marker}]</div>
          <div className="text-slate-600">{conflict.position_b.text}</div>
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: `RefusalNote`**

Create `frontend/app/chat/components/RefusalNote.tsx`:

```tsx
import { RefusalOut } from "@/lib/types/chat";

export function RefusalNote({ refusal }: { refusal: RefusalOut }) {
  return (
    <div className="p-3 bg-slate-50 border border-dashed border-slate-400 rounded-lg text-xs text-slate-600">
      <strong>🔒 {refusal.withheld_count} higher-clearance source(s) may also be relevant.</strong>{" "}
      Request access via Reference{" "}
      <code className="bg-slate-200 px-1 py-0.5 rounded text-[11px]">
        #{refusal.reference_id}
      </code>
      .
    </div>
  );
}
```

- [ ] **Step 5: Typecheck**

```powershell
cd ..\frontend
pnpm exec tsc --noEmit
cd ..\backend
```

Expected: no errors.

- [ ] **Step 6: Commit**

```powershell
git add frontend/components/ClearanceBadge.tsx frontend/app/chat/components/CitationCard.tsx frontend/app/chat/components/ConflictCard.tsx frontend/app/chat/components/RefusalNote.tsx
git commit -m "feat(chat-fe): small components — clearance badge, citation/conflict/refusal cards"
```

---

## Task 16: Frontend message components and inline citation rendering

**Files:**
- Create: `frontend/app/chat/components/MessageUser.tsx`
- Create: `frontend/app/chat/components/MessageAssistant.tsx`
- Create: `frontend/app/chat/components/ChatThread.tsx`
- Create: `frontend/app/chat/components/ChatInput.tsx`

- [ ] **Step 1: `MessageUser`**

Create `frontend/app/chat/components/MessageUser.tsx`:

```tsx
export function MessageUser({ query }: { query: string }) {
  return (
    <div className="self-end max-w-[75%] bg-slate-800 text-slate-100 rounded-2xl rounded-br-md px-4 py-2 text-sm">
      {query}
    </div>
  );
}
```

- [ ] **Step 2: `MessageAssistant` (the centerpiece)**

Create `frontend/app/chat/components/MessageAssistant.tsx`:

```tsx
import React from "react";
import { ChatResponse } from "@/lib/types/chat";
import { CitationCard } from "./CitationCard";
import { ConflictCard } from "./ConflictCard";
import { RefusalNote } from "./RefusalNote";

function renderAnswerText(text: string) {
  const parts = text.split(/(\[\d+\])/);
  return parts.map((token, i) => {
    const m = token.match(/^\[(\d+)\]$/);
    if (!m) return <React.Fragment key={i}>{token}</React.Fragment>;
    const marker = parseInt(m[1], 10);
    return (
      <a
        key={i}
        href={`#cite-${marker}`}
        className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-[11px] font-semibold mx-0.5 hover:bg-blue-200"
      >
        [{marker}]
      </a>
    );
  });
}

export function MessageAssistant({ payload }: { payload: ChatResponse }) {
  return (
    <div className="self-start w-full max-w-[95%] flex flex-col gap-3">
      <div className="bg-slate-50 rounded-2xl rounded-tl-md p-4 text-sm leading-relaxed">
        {renderAnswerText(payload.answer.text)}
      </div>

      {payload.citations.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">
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
          <div className="text-[10px] uppercase tracking-wider text-red-700 mb-1.5">
            ⚠ Conflicts detected · {payload.conflicts.length}
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
        <div className="text-[10px] text-slate-400 italic">
          No citations attached to this answer.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: `ChatInput`**

Create `frontend/app/chat/components/ChatInput.tsx`:

```tsx
"use client";

import { useState } from "react";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (q: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="flex gap-2 p-3 border-t border-slate-200">
      <textarea
        className="flex-1 resize-none border border-slate-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        rows={2}
        placeholder="Ask the archives…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button
        type="button"
        className="bg-slate-800 text-white px-4 rounded-md text-sm disabled:opacity-40"
        disabled={disabled || value.trim().length === 0}
        onClick={submit}
      >
        Send
      </button>
    </div>
  );
}
```

- [ ] **Step 4: `ChatThread`**

Create `frontend/app/chat/components/ChatThread.tsx`:

```tsx
import { ChatResponse } from "@/lib/types/chat";
import { MessageAssistant } from "./MessageAssistant";
import { MessageUser } from "./MessageUser";

export type Turn =
  | { kind: "user"; id: string; query: string }
  | { kind: "assistant"; id: string; payload: ChatResponse }
  | { kind: "assistant-pending"; id: string }
  | { kind: "assistant-error"; id: string; message: string; previousQuery: string };

export function ChatThread({
  turns,
  onRetry,
}: {
  turns: Turn[];
  onRetry: (previousQuery: string) => void;
}) {
  return (
    <div className="flex flex-col gap-5 p-4 overflow-y-auto flex-1">
      {turns.map((t) => {
        switch (t.kind) {
          case "user":
            return <MessageUser key={t.id} query={t.query} />;
          case "assistant":
            return <MessageAssistant key={t.id} payload={t.payload} />;
          case "assistant-pending":
            return (
              <div
                key={t.id}
                className="self-start bg-slate-100 rounded-2xl rounded-tl-md p-4 text-sm text-slate-500 animate-pulse"
              >
                Searching the archives…
              </div>
            );
          case "assistant-error":
            return (
              <div
                key={t.id}
                className="self-start border border-red-300 bg-red-50 rounded-lg p-3 text-sm text-red-800"
              >
                {t.message}
                <button
                  className="ml-3 underline text-red-900"
                  onClick={() => onRetry(t.previousQuery)}
                >
                  Retry
                </button>
              </div>
            );
        }
      })}
    </div>
  );
}
```

- [ ] **Step 5: Typecheck**

```powershell
cd ..\frontend
pnpm exec tsc --noEmit
cd ..\backend
```

Expected: no errors.

- [ ] **Step 6: Commit**

```powershell
git add frontend/app/chat/components/MessageUser.tsx frontend/app/chat/components/MessageAssistant.tsx frontend/app/chat/components/ChatInput.tsx frontend/app/chat/components/ChatThread.tsx
git commit -m "feat(chat-fe): message components with inline citation chips and thread renderer"
```

---

## Task 17: `/chat` page with auth gate, empty state, error state

**Files:**
- Create: `frontend/app/chat/page.tsx`

- [ ] **Step 1: Implement the page**

Create `frontend/app/chat/page.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LLMUnavailableError, postChatAsk } from "@/lib/chat-api";
import { ClearanceBadge } from "@/components/ClearanceBadge";
import { Clearance } from "@/lib/types/chat";
import { ChatInput } from "./components/ChatInput";
import { ChatThread, Turn } from "./components/ChatThread";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface MeResponse {
  id: string;
  username: string;
  role: string;
  max_clearance: Clearance;
  departments: string[];
  tenant: { id: string; name: string; role_label: string };
}

const SUGGESTED = [
  "What's the dress-code policy for off-base events?",
  "What is the reactor coolant shutdown sequence?",
];

let _idCounter = 0;
function nextId() {
  _idCounter += 1;
  return `t${_idCounter}`;
}

export default function ChatPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
      if (res.status === 401) {
        router.replace("/login?next=/chat");
        return;
      }
      if (!res.ok) return;
      setMe((await res.json()) as MeResponse);
    })();
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send(query: string) {
    const userTurn: Turn = { kind: "user", id: nextId(), query };
    const pendingTurn: Turn = { kind: "assistant-pending", id: nextId() };
    setTurns((t) => [...t, userTurn, pendingTurn]);
    setSending(true);
    try {
      const payload = await postChatAsk(query);
      setTurns((t) =>
        t.map((x) =>
          x.id === pendingTurn.id ? { kind: "assistant", id: x.id, payload } : x
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

  if (!me) {
    return <div className="p-6 text-sm text-slate-500">Loading…</div>;
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="px-4 py-2 border-b border-slate-200 flex items-center gap-3 text-sm">
        <span className="font-semibold">{me.tenant.name}</span>
        <span className="text-slate-400">·</span>
        <span>{me.username}</span>
        <span className="text-slate-400">·</span>
        <ClearanceBadge classification={me.max_clearance} />
        <span className="text-[11px] text-slate-500">
          ({me.departments.join(", ")})
        </span>
      </header>

      {turns.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="max-w-md text-center">
            <div className="mb-4 text-sm text-slate-600">
              Welcome, {me.tenant.role_label}. Try a question:
            </div>
            <div className="flex flex-col gap-2">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="border border-slate-200 rounded-lg px-3 py-2 text-sm text-left hover:bg-slate-50"
                  onClick={() => send(q)}
                  disabled={sending}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <ChatThread turns={turns} onRetry={(q) => send(q)} />
      )}
      <div ref={bottomRef} />

      <ChatInput onSend={send} disabled={sending} />
    </div>
  );
}
```

- [ ] **Step 2: Typecheck and run dev server**

```powershell
cd ..\frontend
pnpm exec tsc --noEmit
pnpm dev
```

Expected: typechecks; dev server starts at http://localhost:3000.

- [ ] **Step 3: Sanity-click in browser**

In another terminal, start the backend if not running:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

In the browser:
1. Open `http://localhost:3000/chat` — should redirect to `/login?next=/chat`.
2. Log in as `executive.procurement` / `imperial-march` (use the existing login form).
3. After login, you should see the `/chat` page with the empty state and two suggested questions.
4. Click the dress-code suggestion. Expect a 30–90 s wait (first BGE load + first Groq call), then an assistant message with citations and (depending on the corpus) a conflict card.

If anything fails to render, fix the smallest necessary thing and re-run; do not yet commit.

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/chat/page.tsx
git commit -m "feat(chat-fe): /chat page with auth gate, suggested-question empty state, error retries"
```

---

## Task 18: End-to-end demo verification + docs

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`

- [ ] **Step 1: Run the full demo checklist manually**

With `uvicorn` + `pnpm dev` running, walk every checkbox from [the spec exit checklist](../specs/2026-06-28-phase-c-conflict-detection-chat.md#71-end-of-phase-demo-checklist). Take note of any deviations.

For each demo path:
- Log in as the named user.
- Ask the named question.
- Confirm citations, conflict card (or absence), refusal block (or absence) match the spec.
- Click an inline `[n]` chip → confirm scroll to the matching citation card.

Verify audit rows:

```powershell
psql -h localhost -p 5433 -U postgres -d holocron -c "SELECT event_type, COUNT(*) FROM audit_events GROUP BY event_type ORDER BY event_type;"
```

Expected: at least one `query`, one `response`, and (where the demo path produced one) `refusal` row.

- [ ] **Step 2: Run full backend test suite**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -v
```

Expected: ~104 passing in <30 s default, 4 deselected slow.

Optional:

```powershell
python -m pytest -v -m slow
```

Expected: 4 passing including the real-spaCy and real-Groq tests (requires `GROQ_API_KEY` in `.env`).

- [ ] **Step 3: Update CLAUDE.md**

Edit `CLAUDE.md`:

1. In the "Phase status" section, change:
   - "Phase C — Conflict Detection + Frontend: ⏭ next" → "Phase C — Conflict Detection + Frontend: ✅ done (entity extraction, conflict detection, answer generation, /chat frontend)"
   - "Phase D — Eval + Audit + Polish: pending" → "Phase D — Eval + Audit + Polish: ⏭ next"
2. In the "Tech stack as actually built" table, add a row for **NLP** = "spaCy `en_core_web_sm` (NER + lemma-lowered noun_chunks) for ingest-time entity extraction".
3. In the "Local dev quickstart" backend section, add after the `pip install -e ".[dev]"` line:
   ```powershell
   python -m spacy download en_core_web_sm           # one-time, ~50 MB
   ```
4. Add a "Phase B additions" → "Phase C additions" section under "Critical conventions" with the following bullets:
   - `chunks.entities` is now populated by spaCy at ingest. The `_load_spacy` factory disables parser+lemmatizer pipelines but tagger lemmatization still produces `token.lemma_`.
   - `LLMClient` Protocol covers BOTH the conflict-judge path (`complete_json`) and the answer-generation path (`complete_text`). Production = `GroqLLMClient` with 6-attempt retry ladder (3 primary + 3 fallback). Tests inject `FakeLLMClient` with scripted responses.
   - Conflict cache is module-global in `services/conflict_detection/judge.py` keyed on sorted `(chunk_id_a, chunk_id_b)` tuples, capacity 256, LRU-evicted. Cleared by `_judge_cache_clear()` in tests.
   - `RetrievalResult` now carries `lineage_id` and `entities` so the conflict prefilter has everything it needs without a second DB round-trip.
   - `services/answer_generation/` implements the LlamaIndex `CompactAndRefine` *pattern* (compact context block + single LLM call) without using the LlamaIndex synthesizer object directly. This keeps the retry/fallback policy in one place and tests deterministic. The refine template is provided for future-proofing only.
5. In "What's needed before Phase D starts", document any Phase-C-discovered follow-ups (carry-overs, anything surprising during demo).

- [ ] **Step 4: Write completion record**

Create `docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md`:

```markdown
# Phase C — Conflict Detection + Chat Frontend: Completion Record

Date verified: <fill in>
Branch: <fill in>

## End-of-phase demo checklist

[Copy the §7.1 checklist from the spec and check each box, with one-line evidence per item — see the Phase B completion record for the format.]

## Notable plan deviations (and why)

[List anything that diverged from the plan: file moves, API tweaks, prompt edits that emerged during execution, etc. If nothing diverged, write: "None — plan executed as written."]

## Spec coverage

- §1.3 locked decisions (all 13): implemented as written.
- §2 module layout: implemented; minor refinements noted above (if any).
- §3 conflict-detection pipeline: full — entity extraction, prefilter thresholds, judge with cache, orchestrator.
- §4 answer generation: full — prompts, citation parser, generate_answer service.
- §5 API contract: full — POST /chat/ask, 200/400/401/503 responses, audit writes.
- §6 frontend: full — /chat page, components, inline citation chips, refusal/conflict cards.
- §7 exit criteria: all checklist items in §7.1 verified.

## Known follow-ups for Phase D

- /admin/documents upload + list page
- /admin/audit viewer
- Disk cache for Groq responses (eval-driven)
- structlog → JSON stdout
- Evaluation harness + golden_set.yaml + make eval
- arq + Redis worker
- [Add anything else surfaced during Phase C]
```

- [ ] **Step 5: Commit**

```powershell
git add CLAUDE.md docs/superpowers/plans/2026-06-28-phase-c-conflict-detection-chat-completion.md
git commit -m "docs(phase-c): completion record and Phase D handoff"
```

---

## Notes for the executor

- **TDD discipline**: Every task starts with a failing test, ends with a passing test and a commit. If a test passes before you write the implementation, the test is wrong — fix it before continuing.
- **Cache state in tests**: The conflict judge cache is module-global. Tests that exercise the judge MUST call `_judge_cache_clear()` first. The test fixtures in the plan show this.
- **Phase B tests that touch `RetrievalResult`**: Task 5 adds two fields. Any existing test that constructs `RetrievalResult(...)` needs `lineage_id=` and `entities=` added. Use `python -m pytest -v` after that change to find the failures.
- **Async + httpx**: The chat endpoint test uses `ASGITransport` to drive the FastAPI app in-process. If the existing Phase A/B endpoint tests use a different pattern (e.g. `TestClient`), match that pattern instead.
- **spaCy on Windows**: If `python -m spacy download en_core_web_sm` is slow or fails on a corporate network, the model can be installed directly with `pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz` (or whatever version your spaCy resolves to). The slow test in Task 2 confirms the install worked.
- **First `/chat/ask` is slow**: 60+ seconds for the first call after a fresh uvicorn process (lazy BGE + lazy spaCy + lazy Groq client init). This is the same Phase B behavior; do not optimize.
- **Commit cadence**: ~18 commits if you follow the plan exactly. Squash on review if you prefer larger logical chunks.
