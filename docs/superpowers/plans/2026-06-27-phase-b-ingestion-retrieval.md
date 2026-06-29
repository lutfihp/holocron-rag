# HOLOCRON Phase B — Ingestion + Classification-Aware Retrieval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the synthetic Imperial corpus + the ingestion pipeline that loads it + a hybrid (BM25 + vector) retrieval endpoint with classification-aware RBAC filtering and honest-refusal reference IDs.

**Architecture:** Local BGE embeddings (no API), LlamaIndex for chunking, Postgres tsvector + pgvector for retrieval, RRF for fusion. Strict TDD with a `FakeEmbeddingProvider` seam so every automated test is deterministic and runs in milliseconds.

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.x async, asyncpg, LlamaIndex core 0.12, `sentence-transformers` + `BAAI/bge-base-en-v1.5` (768-d), pgvector, Alembic, pytest.

**Spec source-of-truth:** [docs/superpowers/specs/2026-06-27-phase-b-ingestion-retrieval.md](../specs/2026-06-27-phase-b-ingestion-retrieval.md)

**Plan refinement of the spec's module layout:** the spec's `services/retrieval/{bm25.py,vector.py}` submodules collapse into methods on `ChunkRepository`. Rationale: repositories own SQL; services orchestrate. Sub-modules with one method each don't earn their keep. The spec's other modules (`rrf.py`, `refusal.py`, `__init__.py`) stay as written.

---

## Convention reminders for the executing engineer

- We're on Windows + PowerShell. Use `.\.venv\Scripts\Activate.ps1` to activate the venv.
- Tests run with `python -m pytest -v` from `backend/` after activating the venv.
- Existing 30 tests must stay green after every task. **Run the full suite at every commit step**, not just the new tests.
- The per-test DB fixture in `tests/conftest.py` drops & recreates schema each test. ORM model additions get picked up automatically — no migration edits required for tests to see them.
- `tenants.role_label_map` column is JSONB at the SQL level but uses `JSON` in the ORM; do **not** change this.
- Roles + clearance are TEXT + CHECK constraint, **not** Postgres ENUM. (Documented Phase A deviation.) Continue this pattern.

---

# Phase B.1 — Foundations

## Task 1: Add Phase B dependencies to `pyproject.toml`

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add the runtime deps**

Replace the `dependencies = [...]` block in [backend/pyproject.toml](../../../backend/pyproject.toml) with:

```toml
dependencies = [
    "fastapi>=0.115,<0.116",
    "uvicorn[standard]>=0.32,<0.33",
    "pydantic>=2.9,<3.0",
    "pydantic-settings>=2.6,<3.0",
    "sqlalchemy[asyncio]>=2.0.36,<2.1",
    "asyncpg>=0.30,<0.31",
    "alembic>=1.14,<1.15",
    "bcrypt>=4.2,<5.0",
    "pyjwt>=2.10,<3.0",
    "python-multipart>=0.0.20,<0.1",
    # Phase B
    "llama-index-core>=0.12,<0.13",
    "llama-index-embeddings-huggingface>=0.4,<0.5",
    "sentence-transformers>=3.0,<4.0",
    "python-frontmatter>=1.1,<2.0",
    "pgvector>=0.3,<0.4",
    "numpy>=1.26,<3.0",
]
```

- [ ] **Step 2: Install**

Run from repo root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Expected: install completes successfully. Heads-up — sentence-transformers pulls in PyTorch CPU (~1.5 GB). First install takes 2–5 minutes.

- [ ] **Step 3: Verify imports work**

Run:

```powershell
python -c "import llama_index.core; import frontmatter; from pgvector.sqlalchemy import Vector; from sentence_transformers import SentenceTransformer; print('ok')"
```

Expected: `ok` printed, no errors.

- [ ] **Step 4: Confirm existing suite still green**

```powershell
python -m pytest -v
```

Expected: 30 tests pass, 0 fail.

- [ ] **Step 5: Commit**

```powershell
git add backend/pyproject.toml
git commit -m "deps(backend): add Phase B runtime dependencies"
```

---

## Task 2: `ClearanceContext` and `allowed_levels` helper

**Files:**
- Create: `backend/app/core/clearance.py`
- Test: `backend/tests/test_clearance.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_clearance.py](../../../backend/tests/test_clearance.py) with:

```python
import uuid

import pytest

from app.core.clearance import CLEARANCE_RANK, ClearanceContext, allowed_levels


def test_clearance_rank_total_order():
    assert CLEARANCE_RANK["public"] < CLEARANCE_RANK["restricted"]
    assert CLEARANCE_RANK["restricted"] < CLEARANCE_RANK["secret"]
    assert CLEARANCE_RANK["secret"] < CLEARANCE_RANK["top_secret"]


def test_allowed_levels_employee_sees_only_public():
    assert set(allowed_levels("public")) == {"public"}


def test_allowed_levels_manager_sees_public_and_restricted():
    assert set(allowed_levels("restricted")) == {"public", "restricted"}


def test_allowed_levels_director_sees_through_secret():
    assert set(allowed_levels("secret")) == {"public", "restricted", "secret"}


def test_allowed_levels_executive_sees_all():
    assert set(allowed_levels("top_secret")) == {"public", "restricted", "secret", "top_secret"}


def test_allowed_levels_unknown_raises():
    with pytest.raises(KeyError):
        allowed_levels("alien")


def test_clearance_context_is_frozen():
    ctx = ClearanceContext(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        max_clearance="restricted",
        departments=("hr",),
    )
    with pytest.raises(AttributeError):
        ctx.max_clearance = "secret"  # type: ignore[misc]
```

- [ ] **Step 2: Run the tests; expect failure**

```powershell
python -m pytest tests/test_clearance.py -v
```

Expected: ImportError on `app.core.clearance` — module not yet created.

- [ ] **Step 3: Implement**

Create [backend/app/core/clearance.py](../../../backend/app/core/clearance.py):

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass

CLEARANCE_RANK: dict[str, int] = {
    "public": 0,
    "restricted": 1,
    "secret": 2,
    "top_secret": 3,
}


def allowed_levels(max_clearance: str) -> list[str]:
    """Return all classification labels at or below the user's clearance."""
    max_rank = CLEARANCE_RANK[max_clearance]
    return [label for label, rank in CLEARANCE_RANK.items() if rank <= max_rank]


@dataclass(frozen=True)
class ClearanceContext:
    """Immutable RBAC context required by every chunk read.

    Holding a ClearanceContext is a type-level proof that the caller has
    presented the user's clearance + departments. There is no public chunk
    read API that does not take one.
    """

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    max_clearance: str
    departments: tuple[str, ...]
```

- [ ] **Step 4: Run tests; expect green**

```powershell
python -m pytest tests/test_clearance.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 36 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/core/clearance.py backend/tests/test_clearance.py
git commit -m "feat(core): add ClearanceContext and allowed_levels helper"
```

---

## Task 3: Domain entities for Phase B

**Files:**
- Create: `backend/app/domain/document.py`
- Create: `backend/app/domain/chunk.py`
- Test: `backend/tests/test_domain_phase_b.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_domain_phase_b.py](../../../backend/tests/test_domain_phase_b.py):

```python
import datetime as dt
import uuid

import pytest

from app.domain.chunk import RefusalContext, RetrievalResult, SearchResponse
from app.domain.document import DocumentFrontmatter


def test_document_frontmatter_construction():
    fm = DocumentFrontmatter(
        title="Reactor Manual",
        classification="restricted",
        department="engineering",
        version="2.3",
        effective_date=dt.date(2023, 8, 1),
        lineage_id="reactor-manual",
    )
    assert fm.title == "Reactor Manual"
    assert fm.classification == "restricted"


def test_document_frontmatter_rejects_invalid_classification():
    with pytest.raises(ValueError):
        DocumentFrontmatter(
            title="x",
            classification="alien",
            department="engineering",
            version="1.0",
            effective_date=dt.date(2020, 1, 1),
            lineage_id="x",
        )


def test_retrieval_result_required_fields():
    rr = RetrievalResult(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="t",
        classification="public",
        department="hr",
        effective_date=dt.date(2020, 1, 1),
        snippet="...",
        score=0.5,
        rank=1,
    )
    assert rr.rank == 1


def test_refusal_context_holds_ref_id_and_withheld_ids():
    wid = uuid.uuid4()
    rc = RefusalContext(reference_id="A7F2-CXJK", withheld_count=1, withheld_ids=(wid,))
    assert rc.reference_id == "A7F2-CXJK"
    assert rc.withheld_ids == (wid,)


def test_search_response_optional_refusal_default_none():
    sr = SearchResponse(results=())
    assert sr.refusal is None
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_domain_phase_b.py -v
```

Expected: ImportError on the missing modules.

- [ ] **Step 3: Implement `document.py`**

Create [backend/app/domain/document.py](../../../backend/app/domain/document.py):

```python
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.core.clearance import CLEARANCE_RANK

VALID_CLASSIFICATIONS = frozenset(CLEARANCE_RANK)


@dataclass(frozen=True)
class DocumentFrontmatter:
    title: str
    classification: str
    department: str
    version: str
    effective_date: dt.date
    lineage_id: str

    def __post_init__(self) -> None:
        if self.classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"invalid classification {self.classification!r}; expected one of {sorted(VALID_CLASSIFICATIONS)}"
            )
        if not self.title.strip():
            raise ValueError("title must be non-empty")
        if not self.department.strip():
            raise ValueError("department must be non-empty")
        if not self.lineage_id.strip():
            raise ValueError("lineage_id must be non-empty")
```

- [ ] **Step 4: Implement `chunk.py`**

Create [backend/app/domain/chunk.py](../../../backend/app/domain/chunk.py):

```python
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field


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


@dataclass(frozen=True)
class RefusalContext:
    reference_id: str
    withheld_count: int
    withheld_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[RetrievalResult, ...] = field(default_factory=tuple)
    refusal: RefusalContext | None = None
```

- [ ] **Step 5: Run tests; expect pass**

```powershell
python -m pytest tests/test_domain_phase_b.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Full suite green**

```powershell
python -m pytest -v
```

Expected: 41 tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/domain/document.py backend/app/domain/chunk.py backend/tests/test_domain_phase_b.py
git commit -m "feat(domain): add DocumentFrontmatter and retrieval value objects"
```

---

## Task 4: ORM models for `documents`, `chunks`, `audit_events`

**Files:**
- Modify: `backend/app/domain/models.py`
- Test: `backend/tests/test_models_phase_b.py`

The migration already created these tables (Phase A migration 0001). This task adds ORM mappings so `Base.metadata.create_all` (used by the test fixture) builds a matching schema and so repositories can use the ORM.

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_models_phase_b.py](../../../backend/tests/test_models_phase_b.py):

```python
import datetime as dt
import uuid

import pytest

from app.domain.models import AuditEvent, Chunk, Document


@pytest.mark.asyncio
async def test_can_insert_and_read_document(db_session, empire_tenant):
    doc = Document(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        title="Employee Handbook",
        source_uri="corpus/hr/employee_handbook_2019.md",
        classification="public",
        department="hr",
        version="1.0",
        effective_date=dt.date(2019, 4, 12),
        lineage_id=uuid.uuid4(),
    )
    db_session.add(doc)
    await db_session.flush()
    assert doc.id is not None


@pytest.mark.asyncio
async def test_can_insert_and_read_chunk(db_session, empire_tenant):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    db_session.add(
        Document(
            id=doc_id,
            tenant_id=empire_tenant.id,
            title="t",
            classification="public",
            department="hr",
            version="1.0",
            effective_date=dt.date(2019, 1, 1),
            lineage_id=lineage,
        )
    )
    await db_session.flush()

    chunk = Chunk(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        document_id=doc_id,
        ordinal=0,
        text_="hello world",
        embedding=[0.1] * 768,
        classification="public",
        department="hr",
        effective_date=dt.date(2019, 1, 1),
        lineage_id=lineage,
    )
    db_session.add(chunk)
    await db_session.flush()
    assert chunk.id is not None
    assert chunk.entities == []


@pytest.mark.asyncio
async def test_can_insert_audit_event(db_session, empire_tenant):
    evt = AuditEvent(
        tenant_id=empire_tenant.id,
        user_id=uuid.uuid4(),
        event_type="query",
        query_text="hello",
        retrieved_ids=[uuid.uuid4()],
    )
    db_session.add(evt)
    await db_session.flush()
    assert evt.id is not None  # BIGSERIAL auto-assigned
```

- [ ] **Step 2: Run; expect import or attribute error**

```powershell
python -m pytest tests/test_models_phase_b.py -v
```

Expected: ImportError on `Chunk`, `Document`, `AuditEvent`.

- [ ] **Step 3: Extend `models.py`**

Append to [backend/app/domain/models.py](../../../backend/app/domain/models.py) (keep the existing `Base`, `Tenant`, `User`):

```python
import datetime as dt

from sqlalchemy import BigInteger, Computed, Date, ForeignKey, Integer, JSON, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from pgvector.sqlalchemy import Vector


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    lineage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text_: Mapped[str] = mapped_column("text", String, nullable=False)
    text_tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True), nullable=False
    )
    embedding: Mapped[Any] = mapped_column(Vector(768), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    lineage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entities: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    def __init__(self, **kw):
        kw.setdefault("entities", [])
        super().__init__(**kw)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    query_text: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieved_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    withheld_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    refusal_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    response_text: Mapped[str | None] = mapped_column(String, nullable=True)
    conflicts_found: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
```

**Note on the `text_` mapping:** the SQL column is named `text`. `text` is a SQLAlchemy import we already use (`from sqlalchemy import ... text`), so the Python attribute is `text_` and the column name override `"text"` keeps the SQL identical. Repository code reads/writes via `chunk.text_`.

**Also at the top of [models.py](../../../backend/app/domain/models.py), confirm the existing import set includes `TIMESTAMP` and that the new imports above are merged in (do not duplicate `text` etc).**

- [ ] **Step 4: Verify pgvector extension is available in test DB**

The Phase A migration creates `CREATE EXTENSION vector;` but the test fixture uses `metadata.create_all`, which does NOT run migrations. So the test DB needs the `vector` extension pre-created. Edit [backend/tests/conftest.py](../../../backend/tests/conftest.py) to ensure it:

```python
# Inside the db_session fixture, after `async with engine.begin() as conn:` and BEFORE `drop_all`:
        async with engine.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5: Run the new tests; expect pass**

```powershell
python -m pytest tests/test_models_phase_b.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Full suite green**

```powershell
python -m pytest -v
```

Expected: 44 tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/domain/models.py backend/tests/test_models_phase_b.py backend/tests/conftest.py
git commit -m "feat(domain): add Document, Chunk, AuditEvent ORM models"
```

---

## Task 5: `DocumentRepository`

**Files:**
- Create: `backend/app/repositories/document_repository.py`
- Test: `backend/tests/test_document_repository.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_document_repository.py](../../../backend/tests/test_document_repository.py):

```python
import datetime as dt
import uuid

import pytest

from app.domain.models import Document
from app.repositories.document_repository import DocumentRepository


def _make_doc(tenant_id, *, title="t", department="hr", classification="public",
              source_uri="corpus/hr/t.md", lineage_id=None):
    return Document(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title=title,
        source_uri=source_uri,
        classification=classification,
        department=department,
        version="1.0",
        effective_date=dt.date(2020, 1, 1),
        lineage_id=lineage_id or uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_insert_and_get_by_id(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    doc = _make_doc(empire_tenant.id)
    await repo.insert(doc)

    fetched = await repo.get_by_id(tenant_id=empire_tenant.id, document_id=doc.id)
    assert fetched is not None
    assert fetched.title == "t"


@pytest.mark.asyncio
async def test_get_by_id_scoped_to_tenant(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    doc = _make_doc(empire_tenant.id)
    await repo.insert(doc)

    other_tenant = uuid.uuid4()
    assert await repo.get_by_id(tenant_id=other_tenant, document_id=doc.id) is None


@pytest.mark.asyncio
async def test_delete_by_source_uri_prefix(db_session, empire_tenant):
    repo = DocumentRepository(db_session)
    await repo.insert(_make_doc(empire_tenant.id, source_uri="corpus/hr/a.md"))
    await repo.insert(_make_doc(empire_tenant.id, source_uri="corpus/eng/b.md"))
    await repo.insert(_make_doc(empire_tenant.id, source_uri="other/c.md"))
    await db_session.flush()

    deleted = await repo.delete_by_source_prefix(tenant_id=empire_tenant.id, prefix="corpus/")
    assert deleted == 2
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_document_repository.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/repositories/document_repository.py](../../../backend/app/repositories/document_repository.py):

```python
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        return document

    async def get_by_id(
        self, *, tenant_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document | None:
        stmt = select(Document).where(
            Document.tenant_id == tenant_id, Document.id == document_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete_by_source_prefix(self, *, tenant_id: uuid.UUID, prefix: str) -> int:
        stmt = (
            delete(Document)
            .where(Document.tenant_id == tenant_id)
            .where(Document.source_uri.like(f"{prefix}%"))
        )
        result = await self._session.execute(stmt)
        return result.rowcount or 0
```

- [ ] **Step 4: Run tests; expect green**

```powershell
python -m pytest tests/test_document_repository.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 47 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/repositories/document_repository.py backend/tests/test_document_repository.py
git commit -m "feat(repositories): add DocumentRepository"
```

---

## Task 6: `ChunkRepository` — RBAC-typed reads

This is the core RBAC enforcement boundary. Every read takes a `ClearanceContext`. The unfiltered top-N method (for refusal counting) is named explicitly so its use is grep-able.

**Files:**
- Create: `backend/app/repositories/chunk_repository.py`
- Test: `backend/tests/test_chunk_repository.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_chunk_repository.py](../../../backend/tests/test_chunk_repository.py):

```python
import datetime as dt
import uuid

import pytest

from app.core.clearance import ClearanceContext
from app.domain.models import Chunk, Document
from app.repositories.chunk_repository import ChunkRepository


async def _make_doc_and_chunk(
    session, tenant_id, *, classification, department, text, embedding=None
):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    session.add(
        Document(
            id=doc_id,
            tenant_id=tenant_id,
            title="t",
            classification=classification,
            department=department,
            version="1.0",
            effective_date=dt.date(2020, 1, 1),
            lineage_id=lineage,
        )
    )
    chunk = Chunk(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        document_id=doc_id,
        ordinal=0,
        text_=text,
        embedding=embedding or [0.0] * 768,
        classification=classification,
        department=department,
        effective_date=dt.date(2020, 1, 1),
        lineage_id=lineage,
    )
    session.add(chunk)
    await session.flush()
    return chunk


def _ctx(tenant_id, max_clearance, departments):
    return ClearanceContext(
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        max_clearance=max_clearance,
        departments=tuple(departments),
    )


@pytest.mark.asyncio
async def test_bm25_topn_filters_by_clearance(db_session, empire_tenant):
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="hr",
                              text="dress code policy applies to all")
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="secret", department="hr",
                              text="dress code exception protocols")

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    results = await repo.bm25_topn(ctx, query="dress code", n=10)

    assert len(results) == 1
    assert results[0].classification == "public"


@pytest.mark.asyncio
async def test_bm25_topn_filters_by_department(db_session, empire_tenant):
    # public docs ARE visible regardless of department
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="engineering",
                              text="public engineering memo")
    # restricted requires matching department
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="restricted", department="engineering",
                              text="restricted engineering memo")

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "secret", ["hr"])  # HR director, no eng
    results = await repo.bm25_topn(ctx, query="engineering memo", n=10)
    classifications = sorted(r.classification for r in results)
    # restricted eng excluded; public eng included
    assert "secret" not in classifications
    assert "restricted" not in classifications
    assert "public" in classifications


@pytest.mark.asyncio
async def test_bm25_topn_tenant_scoped(db_session, empire_tenant):
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="hr",
                              text="visible chunk")
    repo = ChunkRepository(db_session)
    other = _ctx(uuid.uuid4(), "top_secret", ["hr"])
    assert await repo.bm25_topn(other, query="visible chunk", n=10) == []


@pytest.mark.asyncio
async def test_vector_topn_filters_by_clearance(db_session, empire_tenant):
    target = [0.1] * 768
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="hr",
                              text="anything", embedding=target)
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="secret", department="hr",
                              text="anything else", embedding=target)

    repo = ChunkRepository(db_session)
    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    results = await repo.vector_topn(ctx, query_vector=target, n=10)
    assert all(r.classification == "public" for r in results)


@pytest.mark.asyncio
async def test_unfiltered_topn_ids_ignores_rbac(db_session, empire_tenant):
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="hr",
                              text="dress code policy")
    secret = await _make_doc_and_chunk(db_session, empire_tenant.id,
                                       classification="top_secret", department="security",
                                       text="dress code clearance protocols")

    repo = ChunkRepository(db_session)
    ids = await repo.unfiltered_topn_ids(
        tenant_id=empire_tenant.id,
        query="dress code",
        query_vector=[0.1] * 768,
        n=25,
    )
    assert secret.id in ids


@pytest.mark.asyncio
async def test_unfiltered_topn_ids_still_tenant_scoped(db_session, empire_tenant):
    await _make_doc_and_chunk(db_session, empire_tenant.id,
                              classification="public", department="hr",
                              text="dress code")
    repo = ChunkRepository(db_session)
    ids = await repo.unfiltered_topn_ids(
        tenant_id=uuid.uuid4(),
        query="dress code",
        query_vector=[0.1] * 768,
        n=25,
    )
    assert ids == set()


@pytest.mark.asyncio
async def test_bulk_insert_chunks(db_session, empire_tenant):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    db_session.add(
        Document(
            id=doc_id, tenant_id=empire_tenant.id, title="t",
            classification="public", department="hr", version="1.0",
            effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
    )
    await db_session.flush()

    chunks = [
        Chunk(
            id=uuid.uuid4(), tenant_id=empire_tenant.id, document_id=doc_id, ordinal=i,
            text_=f"chunk {i}", embedding=[0.0] * 768, classification="public",
            department="hr", effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
        for i in range(3)
    ]
    repo = ChunkRepository(db_session)
    inserted = await repo.bulk_insert(chunks)
    assert inserted == 3
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_chunk_repository.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/repositories/chunk_repository.py](../../../backend/app/repositories/chunk_repository.py):

```python
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import bindparam, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clearance import ClearanceContext, allowed_levels
from app.domain.models import Chunk


@dataclass(frozen=True)
class ChunkHit:
    """A row from BM25 or vector ranking, with all data needed downstream
    (denormalized title pulled in via join). Score semantics: higher == better
    for BM25; lower distance == better for vector — but we expose `score` as
    the *rank position only* via the `rank` field and keep raw `score` for
    debugging. RRF only needs rank."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    score: float
    rank: int


class ChunkRepository:
    """Type-level RBAC: every read method requires ClearanceContext.

    The one explicit RBAC bypass is `unfiltered_topn_ids`, named so it cannot
    be confused with a normal read. It exists solely for refusal counting.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, chunks: Sequence[Chunk]) -> int:
        for c in chunks:
            self._session.add(c)
        await self._session.flush()
        return len(chunks)

    async def bm25_topn(
        self, ctx: ClearanceContext, *, query: str, n: int
    ) -> list[ChunkHit]:
        sql = sql_text(
            """
            SELECT c.id, c.document_id, d.title, c.classification, c.department,
                   c.effective_date, c.text,
                   ts_rank(c.text_tsv, plainto_tsquery('english', :q)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.tenant_id = :tenant
              AND c.classification = ANY(:allowed)
              AND (c.department = ANY(:depts) OR c.classification = 'public')
              AND c.text_tsv @@ plainto_tsquery('english', :q)
            ORDER BY score DESC
            LIMIT :n
            """
        ).bindparams(
            bindparam("allowed", expanding=False),
            bindparam("depts", expanding=False),
        )
        result = await self._session.execute(
            sql,
            {
                "tenant": ctx.tenant_id,
                "allowed": allowed_levels(ctx.max_clearance),
                "depts": list(ctx.departments),
                "q": query,
                "n": n,
            },
        )
        return [
            ChunkHit(
                chunk_id=row[0], document_id=row[1], document_title=row[2],
                classification=row[3], department=row[4], effective_date=row[5],
                snippet=_snippet(row[6]), score=float(row[7]), rank=i + 1,
            )
            for i, row in enumerate(result.fetchall())
        ]

    async def vector_topn(
        self, ctx: ClearanceContext, *, query_vector: list[float], n: int
    ) -> list[ChunkHit]:
        sql = sql_text(
            """
            SELECT c.id, c.document_id, d.title, c.classification, c.department,
                   c.effective_date, c.text,
                   (c.embedding <=> CAST(:qv AS vector)) AS distance
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.tenant_id = :tenant
              AND c.classification = ANY(:allowed)
              AND (c.department = ANY(:depts) OR c.classification = 'public')
              AND c.embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT :n
            """
        )
        result = await self._session.execute(
            sql,
            {
                "tenant": ctx.tenant_id,
                "allowed": allowed_levels(ctx.max_clearance),
                "depts": list(ctx.departments),
                "qv": _vec_literal(query_vector),
                "n": n,
            },
        )
        return [
            ChunkHit(
                chunk_id=row[0], document_id=row[1], document_title=row[2],
                classification=row[3], department=row[4], effective_date=row[5],
                snippet=_snippet(row[6]),
                score=1.0 - float(row[7]),  # cosine similarity
                rank=i + 1,
            )
            for i, row in enumerate(result.fetchall())
        ]

    async def unfiltered_topn_ids(
        self,
        *,
        tenant_id: uuid.UUID,
        query: str,
        query_vector: list[float],
        n: int,
    ) -> set[uuid.UUID]:
        """RBAC-bypassing union of top-N BM25 + top-N vector. Used ONLY for
        honest-refusal counting. Returns the set of chunk ids that would appear
        in retrieval if the user had unlimited clearance."""

        bm = sql_text(
            """
            SELECT c.id
            FROM chunks c
            WHERE c.tenant_id = :tenant
              AND c.text_tsv @@ plainto_tsquery('english', :q)
            ORDER BY ts_rank(c.text_tsv, plainto_tsquery('english', :q)) DESC
            LIMIT :n
            """
        )
        vec = sql_text(
            """
            SELECT c.id
            FROM chunks c
            WHERE c.tenant_id = :tenant
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:qv AS vector) ASC
            LIMIT :n
            """
        )
        bm_res = await self._session.execute(bm, {"tenant": tenant_id, "q": query, "n": n})
        vec_res = await self._session.execute(
            vec, {"tenant": tenant_id, "qv": _vec_literal(query_vector), "n": n}
        )
        return {r[0] for r in bm_res.fetchall()} | {r[0] for r in vec_res.fetchall()}


def _snippet(text: str, *, max_len: int = 280) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _vec_literal(vec: list[float]) -> str:
    # pgvector accepts a string literal of the form "[0.1, 0.2, ...]" with CAST
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
```

- [ ] **Step 4: Run tests; expect green**

```powershell
python -m pytest tests/test_chunk_repository.py -v
```

Expected: 7 tests pass. If BM25 tests fail because the test DB doesn't have the english text search config, install `postgresql-contrib` is not required — the `english` config ships standard with Postgres. If you see a "text search configuration does not exist" error, your Postgres image is incomplete; verify with `docker compose exec postgres psql -U holocron -d holocron_test -c "SELECT cfgname FROM pg_ts_config;"`.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 54 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/repositories/chunk_repository.py backend/tests/test_chunk_repository.py
git commit -m "feat(repositories): add ChunkRepository with RBAC-typed reads"
```

---

## Task 7: `AuditRepository` (minimal Phase B scope)

**Files:**
- Create: `backend/app/repositories/audit_repository.py`
- Test: `backend/tests/test_audit_repository.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_audit_repository.py](../../../backend/tests/test_audit_repository.py):

```python
import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_insert_query_event(db_session, empire_tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    retrieved = [uuid.uuid4(), uuid.uuid4()]
    await repo.insert_query(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        query_text="dress code policy",
        retrieved_ids=retrieved,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "query"
    assert rows[0].retrieved_ids == retrieved


@pytest.mark.asyncio
async def test_insert_refusal_event(db_session, empire_tenant):
    repo = AuditRepository(db_session)
    user_id = uuid.uuid4()
    withheld = [uuid.uuid4(), uuid.uuid4()]
    await repo.insert_refusal(
        tenant_id=empire_tenant.id,
        user_id=user_id,
        reference_id="A7F2-CXJK",
        retrieved_ids=[],
        withheld_ids=withheld,
    )
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "refusal"
    assert rows[0].refusal_ref == "A7F2-CXJK"
    assert rows[0].withheld_ids == withheld
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_audit_repository.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/repositories/audit_repository.py](../../../backend/app/repositories/audit_repository.py):

```python
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AuditEvent


class AuditRepository:
    """Minimal Phase B audit writer. Full event taxonomy and viewer land in Phase D."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_query(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        query_text: str,
        retrieved_ids: Sequence[uuid.UUID],
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
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
        reference_id: str,
        retrieved_ids: Sequence[uuid.UUID],
        withheld_ids: Sequence[uuid.UUID],
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="refusal",
                refusal_ref=reference_id,
                retrieved_ids=list(retrieved_ids),
                withheld_ids=list(withheld_ids),
            )
        )
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_audit_repository.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 56 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/repositories/audit_repository.py backend/tests/test_audit_repository.py
git commit -m "feat(repositories): add AuditRepository (minimal Phase B scope)"
```

---

# Phase B.2 — Ingestion

## Task 8: `EmbeddingProvider` Protocol + `FakeEmbeddingProvider`

**Files:**
- Create: `backend/app/services/__init__.py` (empty marker)
- Create: `backend/app/services/ingestion/__init__.py` (empty marker for now)
- Create: `backend/app/services/ingestion/embedding.py`
- Test: `backend/tests/test_embedding_fake.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_embedding_fake.py](../../../backend/tests/test_embedding_fake.py):

```python
import numpy as np

from app.services.ingestion.embedding import FakeEmbeddingProvider


def test_same_text_same_vector():
    fake = FakeEmbeddingProvider()
    v1 = fake.embed_one("the dress code applies to all imperial personnel")
    v2 = fake.embed_one("the dress code applies to all imperial personnel")
    assert np.allclose(v1, v2)


def test_vector_dimension_is_768():
    fake = FakeEmbeddingProvider()
    v = fake.embed_one("anything")
    assert v.shape == (768,)


def test_similar_texts_have_higher_cosine_than_unrelated():
    fake = FakeEmbeddingProvider()
    a = fake.embed_one("dress code policy for off-base events")
    b = fake.embed_one("dress code rules for off-base activities")
    c = fake.embed_one("reactor coolant shutdown sequence procedures")

    def cos(x, y):
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))

    assert cos(a, b) > cos(a, c)


def test_embed_batch_returns_one_vector_per_input():
    fake = FakeEmbeddingProvider()
    vecs = fake.embed_batch(["one", "two", "three"])
    assert len(vecs) == 3
    assert all(v.shape == (768,) for v in vecs)
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_embedding_fake.py -v
```

- [ ] **Step 3: Implement**

Create empty marker files:

```powershell
ni backend/app/services/__init__.py -ItemType File
ni backend/app/services/ingestion/__init__.py -ItemType File
```

Create [backend/app/services/ingestion/embedding.py](../../../backend/app/services/ingestion/embedding.py):

```python
from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

EMBEDDING_DIM = 768


class EmbeddingProvider(Protocol):
    """Protocol every embedder implements. Tests inject the Fake; production uses BGE."""

    def embed_one(self, text: str) -> np.ndarray: ...

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]: ...


class FakeEmbeddingProvider:
    """Deterministic hash-based embeddings for tests.

    Strategy: bag-of-overlapping-trigrams hashed into bucket positions. Two texts
    that share many trigrams land closer in vector space than two that don't.
    Not a real semantic embedding — but enough to make 'similar query retrieves
    similar chunk' behavior deterministic for retrieval tests.
    """

    def embed_one(self, text: str) -> np.ndarray:
        v = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        normalized = text.lower().strip()
        if not normalized:
            return v
        # word-level + trigram-level hashing
        for token in normalized.split():
            idx = int(hashlib.blake2b(token.encode("utf-8"), digest_size=4).hexdigest(), 16) % EMBEDDING_DIM
            v[idx] += 1.0
        for i in range(len(normalized) - 2):
            tri = normalized[i : i + 3]
            idx = int(hashlib.blake2b(tri.encode("utf-8"), digest_size=4).hexdigest(), 16) % EMBEDDING_DIM
            v[idx] += 0.5
        norm = float(np.linalg.norm(v))
        if norm > 0:
            v /= norm
        return v

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed_one(t) for t in texts]
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_embedding_fake.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 60 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/__init__.py backend/app/services/ingestion/__init__.py backend/app/services/ingestion/embedding.py backend/tests/test_embedding_fake.py
git commit -m "feat(ingestion): EmbeddingProvider protocol + FakeEmbeddingProvider for tests"
```

---

## Task 9: `BgeEmbeddingProvider` (real, sentence-transformers)

This is the only place in Phase B that talks to a real model. It has a single test that's marked `@pytest.mark.slow` so it's opt-in. The default suite never loads BGE.

**Files:**
- Modify: `backend/app/services/ingestion/embedding.py`
- Modify: `backend/pyproject.toml` (add `slow` marker)
- Test: `backend/tests/test_embedding_bge.py`

- [ ] **Step 1: Register the `slow` marker**

In [backend/pyproject.toml](../../../backend/pyproject.toml), inside `[tool.pytest.ini_options]`, add:

```toml
markers = ["slow: tests that load real ML models or hit external services"]
addopts = "-ra -m 'not slow'"  # replaces the existing addopts line
```

- [ ] **Step 2: Write the (opt-in) test**

Create [backend/tests/test_embedding_bge.py](../../../backend/tests/test_embedding_bge.py):

```python
import numpy as np
import pytest

from app.services.ingestion.embedding import BgeEmbeddingProvider


@pytest.mark.slow
def test_bge_embedding_dimension_is_768():
    bge = BgeEmbeddingProvider()
    v = bge.embed_one("imperial dress code policy")
    assert isinstance(v, np.ndarray)
    assert v.shape == (768,)


@pytest.mark.slow
def test_bge_similar_texts_more_similar_than_unrelated():
    bge = BgeEmbeddingProvider()
    a = bge.embed_one("dress code policy for off-base events")
    b = bge.embed_one("attire guidelines for personnel travel")
    c = bge.embed_one("reactor coolant shutdown sequence")

    def cos(x, y):
        return float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))

    assert cos(a, b) > cos(a, c)
```

- [ ] **Step 3: Run; expect ImportError on Bge**

```powershell
python -m pytest tests/test_embedding_bge.py -v -m slow
```

- [ ] **Step 4: Add BGE impl**

Append to [backend/app/services/ingestion/embedding.py](../../../backend/app/services/ingestion/embedding.py):

```python
class BgeEmbeddingProvider:
    """Local BAAI/bge-base-en-v1.5 via sentence-transformers (768-dim).

    First instantiation downloads ~440 MB. Subsequent runs are cached in
    HF_HOME (default ~/.cache/huggingface).
    """

    _MODEL_NAME = "BAAI/bge-base-en-v1.5"

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import; defer

        self._model = SentenceTransformer(self._MODEL_NAME)

    def embed_one(self, text: str) -> np.ndarray:
        v = self._model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(v, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        arr = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, batch_size=32
        )
        return [np.asarray(row, dtype=np.float32) for row in arr]
```

- [ ] **Step 5: Run the slow test; expect green** (this downloads the model the first time)

```powershell
python -m pytest tests/test_embedding_bge.py -v -m slow
```

Expected: 2 tests pass. First run ~30–60 s for download; subsequent runs ~5 s.

- [ ] **Step 6: Default (non-slow) suite stays fast**

```powershell
python -m pytest -v
```

Expected: 60 tests pass; BGE tests deselected by `-m 'not slow'`. Total runtime under 5 s.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/ingestion/embedding.py backend/tests/test_embedding_bge.py backend/pyproject.toml
git commit -m "feat(ingestion): BgeEmbeddingProvider (sentence-transformers, opt-in slow test)"
```

---

## Task 10: Frontmatter loader

Loads markdown files, splits YAML frontmatter from body, validates frontmatter strictly.

**Files:**
- Create: `backend/app/services/ingestion/loader.py`
- Test: `backend/tests/test_loader.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_loader.py](../../../backend/tests/test_loader.py):

```python
import datetime as dt
import textwrap
from pathlib import Path

import pytest

from app.services.ingestion.loader import LoadedDocument, load_corpus_dir, load_one


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_load_one_parses_frontmatter_and_body(tmp_path):
    p = _write(
        tmp_path,
        "hr/handbook.md",
        textwrap.dedent(
            """\
            ---
            title: Imperial Employee Handbook
            classification: public
            department: hr
            version: "1.0"
            effective_date: 2019-04-12
            lineage_id: employee-handbook
            ---
            # Body
            All Imperial personnel...
            """
        ),
    )
    loaded = load_one(p, corpus_root=tmp_path)
    assert isinstance(loaded, LoadedDocument)
    assert loaded.frontmatter.title == "Imperial Employee Handbook"
    assert loaded.frontmatter.classification == "public"
    assert loaded.frontmatter.effective_date == dt.date(2019, 4, 12)
    assert loaded.source_uri == "corpus/hr/handbook.md"
    assert "All Imperial personnel" in loaded.body


def test_load_one_rejects_missing_frontmatter(tmp_path):
    p = _write(tmp_path, "broken.md", "no frontmatter at all\n")
    with pytest.raises(ValueError, match="frontmatter"):
        load_one(p, corpus_root=tmp_path)


def test_load_one_rejects_invalid_classification(tmp_path):
    p = _write(
        tmp_path,
        "broken.md",
        textwrap.dedent(
            """\
            ---
            title: x
            classification: alien
            department: hr
            version: "1.0"
            effective_date: 2019-04-12
            lineage_id: x
            ---
            body
            """
        ),
    )
    with pytest.raises(ValueError, match="classification"):
        load_one(p, corpus_root=tmp_path)


def test_load_corpus_dir_loads_all_markdown(tmp_path):
    for rel in ["hr/a.md", "engineering/b.md", "engineering/c.md"]:
        _write(
            tmp_path,
            rel,
            textwrap.dedent(
                f"""\
                ---
                title: {rel}
                classification: public
                department: hr
                version: "1"
                effective_date: 2020-01-01
                lineage_id: {rel}
                ---
                body
                """
            ),
        )
    docs = load_corpus_dir(tmp_path)
    assert len(docs) == 3


def test_load_corpus_dir_skips_non_markdown(tmp_path):
    _write(tmp_path, "README.txt", "ignored")
    _write(
        tmp_path,
        "hr/a.md",
        textwrap.dedent(
            """\
            ---
            title: t
            classification: public
            department: hr
            version: "1"
            effective_date: 2020-01-01
            lineage_id: t
            ---
            body
            """
        ),
    )
    docs = load_corpus_dir(tmp_path)
    assert len(docs) == 1
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_loader.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/services/ingestion/loader.py](../../../backend/app/services/ingestion/loader.py):

```python
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from app.domain.document import DocumentFrontmatter


@dataclass(frozen=True)
class LoadedDocument:
    frontmatter: DocumentFrontmatter
    body: str
    source_uri: str  # relative path from repo root, posix-style, e.g. 'corpus/hr/handbook.md'


REQUIRED_KEYS = ("title", "classification", "department", "version", "effective_date", "lineage_id")


def load_one(path: Path, *, corpus_root: Path) -> LoadedDocument:
    post = frontmatter.load(path)
    if not post.metadata or "title" not in post.metadata:
        raise ValueError(f"missing frontmatter in {path}")
    missing = [k for k in REQUIRED_KEYS if k not in post.metadata]
    if missing:
        raise ValueError(f"frontmatter in {path} missing required keys: {missing}")

    eff = post.metadata["effective_date"]
    if isinstance(eff, str):
        eff = dt.date.fromisoformat(eff)
    elif isinstance(eff, dt.datetime):
        eff = eff.date()
    elif not isinstance(eff, dt.date):
        raise ValueError(f"effective_date in {path} must be a date, got {type(eff).__name__}")

    fm = DocumentFrontmatter(
        title=str(post.metadata["title"]).strip(),
        classification=str(post.metadata["classification"]).strip(),
        department=str(post.metadata["department"]).strip(),
        version=str(post.metadata["version"]).strip(),
        effective_date=eff,
        lineage_id=str(post.metadata["lineage_id"]).strip(),
    )

    # build the source_uri relative to corpus_root's parent (so 'corpus/...' is preserved)
    try:
        rel = path.resolve().relative_to(corpus_root.resolve().parent).as_posix()
    except ValueError:
        rel = path.as_posix()

    return LoadedDocument(frontmatter=fm, body=post.content, source_uri=rel)


def load_corpus_dir(root: Path) -> list[LoadedDocument]:
    """Recursively load every *.md file under root. Fails loud on any invalid frontmatter."""
    out: list[LoadedDocument] = []
    for p in sorted(root.rglob("*.md")):
        out.append(load_one(p, corpus_root=root))
    return out
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_loader.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 65 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/ingestion/loader.py backend/tests/test_loader.py
git commit -m "feat(ingestion): frontmatter loader with strict validation"
```

---

## Task 11: Splitter (LlamaIndex SentenceSplitter primary for Phase B)

The spec calls for `SemanticSplitterNodeParser` with `SentenceSplitter` fallback. For Phase B we ship `SentenceSplitter` only and stub the semantic path. **Rationale:** `SemanticSplitter` requires running the BGE model during ingest splitting (multiplies embed calls 2–3×) and the quality lift on enterprise-policy prose is marginal. Phase C can swap if eval signal suggests it.

This deviates from the design doc; document it in `Known follow-ups` at the end.

**Files:**
- Create: `backend/app/services/ingestion/splitter.py`
- Test: `backend/tests/test_splitter.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_splitter.py](../../../backend/tests/test_splitter.py):

```python
from app.services.ingestion.splitter import split_text


def test_short_text_one_chunk():
    chunks = split_text("This is a single short sentence.", chunk_size=512, overlap=50)
    assert chunks == ["This is a single short sentence."]


def test_long_text_multiple_chunks():
    # 30 sentences ~150 chars each → comfortably exceeds chunk_size=512 a few times
    sentences = [f"This is sentence number {i}." for i in range(30)]
    text = " ".join(sentences)
    chunks = split_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    # every chunk respects the size budget (LlamaIndex measures in tokens; we allow some slack)
    for c in chunks:
        assert len(c) <= 400


def test_chunks_preserve_sentence_boundaries():
    sentences = [f"Sentence {i} content here." for i in range(10)]
    text = " ".join(sentences)
    chunks = split_text(text, chunk_size=80, overlap=10)
    # No chunk should begin mid-word
    for c in chunks:
        assert not c.startswith(" ")


def test_empty_text_returns_empty_list():
    assert split_text("", chunk_size=512, overlap=50) == []
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_splitter.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/services/ingestion/splitter.py](../../../backend/app/services/ingestion/splitter.py):

```python
from __future__ import annotations

from llama_index.core.node_parser import SentenceSplitter


def split_text(text: str, *, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Sentence-aware splitter via LlamaIndex.

    chunk_size and overlap are measured in tokens by LlamaIndex's tokenizer.
    """
    if not text.strip():
        return []
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return splitter.split_text(text)
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_splitter.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 69 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/ingestion/splitter.py backend/tests/test_splitter.py
git commit -m "feat(ingestion): sentence-aware splitter (LlamaIndex SentenceSplitter)"
```

---

## Task 12: Ingestion pipeline

Orchestrates loader → splitter → embedder → repository persist.

**Files:**
- Create: `backend/app/services/ingestion/pipeline.py`
- Test: `backend/tests/test_ingestion_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_ingestion_pipeline.py](../../../backend/tests/test_ingestion_pipeline.py):

```python
import datetime as dt
import textwrap
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.domain.models import Chunk, Document
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.pipeline import IngestionReport, ingest_corpus_dir


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _basic_doc(title: str, classification: str = "public", department: str = "hr") -> str:
    return textwrap.dedent(
        f"""\
        ---
        title: {title}
        classification: {classification}
        department: {department}
        version: "1.0"
        effective_date: 2020-01-01
        lineage_id: {title.lower().replace(' ', '-')}
        ---
        # {title}

        This is the first paragraph of {title}. It contains a few sentences. They
        all talk about {title}. {title} matters greatly.

        This is the second paragraph. More sentences here. Still about {title}.
        And again about {title}. Final sentence.
        """
    )


@pytest.mark.asyncio
async def test_ingest_single_doc_persists_document_and_chunks(db_session, empire_tenant, tmp_path):
    corpus = tmp_path / "corpus"
    _write(corpus, "hr/handbook.md", _basic_doc("Imperial Handbook"))

    report = await ingest_corpus_dir(
        corpus,
        tenant_id=empire_tenant.id,
        session=db_session,
        embedder=FakeEmbeddingProvider(),
    )
    assert isinstance(report, IngestionReport)
    assert report.documents_inserted == 1
    assert report.chunks_inserted >= 1

    docs = (await db_session.execute(select(Document))).scalars().all()
    assert len(docs) == 1
    assert docs[0].title == "Imperial Handbook"

    chunks = (await db_session.execute(select(Chunk))).scalars().all()
    assert len(chunks) == report.chunks_inserted
    # ordinals are sequential per-document
    assert sorted(c.ordinal for c in chunks) == list(range(len(chunks)))
    # denormalized fields match parent doc
    assert all(c.classification == "public" for c in chunks)
    assert all(c.department == "hr" for c in chunks)


@pytest.mark.asyncio
async def test_ingest_idempotent_via_source_prefix_delete(db_session, empire_tenant, tmp_path):
    corpus = tmp_path / "corpus"
    _write(corpus, "hr/a.md", _basic_doc("Doc A"))
    _write(corpus, "hr/b.md", _basic_doc("Doc B"))

    embedder = FakeEmbeddingProvider()
    r1 = await ingest_corpus_dir(corpus, tenant_id=empire_tenant.id,
                                 session=db_session, embedder=embedder)
    r2 = await ingest_corpus_dir(corpus, tenant_id=empire_tenant.id,
                                 session=db_session, embedder=embedder)
    assert r1.documents_inserted == r2.documents_inserted == 2

    docs = (await db_session.execute(select(Document))).scalars().all()
    assert len(docs) == 2  # NOT 4 — second run replaced first


@pytest.mark.asyncio
async def test_ingest_tenant_scoped(db_session, empire_tenant, tmp_path):
    corpus = tmp_path / "corpus"
    _write(corpus, "hr/a.md", _basic_doc("Doc A"))
    await ingest_corpus_dir(corpus, tenant_id=empire_tenant.id,
                            session=db_session, embedder=FakeEmbeddingProvider())

    # different tenant; idempotent delete should not touch the empire's docs
    other_tenant = uuid.uuid4()
    # Insert the other tenant row first since FK requires it
    from app.domain.models import Tenant
    db_session.add(Tenant(id=other_tenant, name="Rebel Alliance", role_label_map={}))
    await db_session.flush()
    await ingest_corpus_dir(corpus, tenant_id=other_tenant,
                            session=db_session, embedder=FakeEmbeddingProvider())

    docs = (await db_session.execute(select(Document))).scalars().all()
    assert len(docs) == 2  # one per tenant
    tenants_seen = {d.tenant_id for d in docs}
    assert tenants_seen == {empire_tenant.id, other_tenant}
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_ingestion_pipeline.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/services/ingestion/pipeline.py](../../../backend/app/services/ingestion/pipeline.py):

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chunk, Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.loader import LoadedDocument, load_corpus_dir
from app.services.ingestion.splitter import split_text


@dataclass(frozen=True)
class IngestionReport:
    documents_inserted: int
    chunks_inserted: int


# stable namespace so lineage strings → deterministic UUIDs
_LINEAGE_NS = uuid.UUID("e7b3a2d4-1c5e-4f8a-9b6d-7a3c0f1e2a4b")


def _lineage_uuid(lineage_str: str) -> uuid.UUID:
    return uuid.uuid5(_LINEAGE_NS, lineage_str)


async def ingest_corpus_dir(
    corpus_dir: Path,
    *,
    tenant_id: uuid.UUID,
    session: AsyncSession,
    embedder: EmbeddingProvider,
    source_prefix: str | None = None,
) -> IngestionReport:
    """Idempotent ingest: deletes existing docs under `source_prefix` for this
    tenant, then re-inserts. Default `source_prefix` = '{corpus_dir.name}/'
    (e.g. 'corpus/')."""

    docs = load_corpus_dir(corpus_dir)
    prefix = source_prefix or f"{corpus_dir.name}/"

    doc_repo = DocumentRepository(session)
    chunk_repo = ChunkRepository(session)

    # idempotency: blow away prior ingest for this tenant under this prefix
    await doc_repo.delete_by_source_prefix(tenant_id=tenant_id, prefix=prefix)
    await session.flush()

    total_chunks = 0
    for loaded in docs:
        doc, chunks = _build_doc_and_chunks(loaded, tenant_id=tenant_id, embedder=embedder)
        await doc_repo.insert(doc)
        if chunks:
            await chunk_repo.bulk_insert(chunks)
            total_chunks += len(chunks)

    return IngestionReport(documents_inserted=len(docs), chunks_inserted=total_chunks)


def _build_doc_and_chunks(
    loaded: LoadedDocument, *, tenant_id: uuid.UUID, embedder: EmbeddingProvider
) -> tuple[Document, list[Chunk]]:
    fm = loaded.frontmatter
    lineage = _lineage_uuid(fm.lineage_id)
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        title=fm.title,
        source_uri=loaded.source_uri,
        classification=fm.classification,
        department=fm.department,
        version=fm.version,
        effective_date=fm.effective_date,
        lineage_id=lineage,
    )

    chunk_texts = split_text(loaded.body)
    if not chunk_texts:
        return doc, []

    vectors = embedder.embed_batch(chunk_texts)

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
        )
        for i, (text, vec) in enumerate(zip(chunk_texts, vectors))
    ]
    return doc, chunks
```

**Naming note:** Python kwarg is `text_=...` (the attribute name); the SQL column name is still `"text"` per the column override in [models.py](../../../backend/app/domain/models.py). All reads use `chunk.text_`.

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_ingestion_pipeline.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 72 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/ingestion/pipeline.py backend/tests/test_ingestion_pipeline.py
git commit -m "feat(ingestion): pipeline orchestrating loader → splitter → embedder → persist"
```

---

## Task 13: `scripts/seed_corpus.py` — idempotent CLI

Real CLI invoked from the Makefile. Uses the real `BgeEmbeddingProvider`.

**Files:**
- Create: `backend/scripts/seed_corpus.py`
- Modify: `Makefile`

- [ ] **Step 1: Implement the CLI**

Create [backend/scripts/seed_corpus.py](../../../backend/scripts/seed_corpus.py):

```python
"""Seed the corpus directory into the live DB. Idempotent.

Run via `make seed-corpus` (assumes the venv is active and `make backend-seed`
has been run once to seed the Imperial tenant).
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from sqlalchemy import select

from app.core.database import get_sessionmaker
from app.domain.models import Tenant
from app.services.ingestion.embedding import BgeEmbeddingProvider
from app.services.ingestion.pipeline import ingest_corpus_dir

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"
EMPIRE_NAME = "Galactic Empire"


async def main() -> int:
    if not CORPUS_DIR.exists():
        print(f"ERROR: corpus dir not found: {CORPUS_DIR}", file=sys.stderr)
        return 1

    Session = get_sessionmaker()
    async with Session() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.name == EMPIRE_NAME))
        ).scalar_one_or_none()
        if tenant is None:
            print(
                f"ERROR: tenant '{EMPIRE_NAME}' not found. Run `make backend-seed` first.",
                file=sys.stderr,
            )
            return 1

        print(f"Loading BGE model (first run downloads ~440 MB)...")
        embedder = BgeEmbeddingProvider()

        print(f"Ingesting from {CORPUS_DIR} into tenant {tenant.id}...")
        t0 = time.time()
        report = await ingest_corpus_dir(
            CORPUS_DIR, tenant_id=tenant.id, session=session, embedder=embedder
        )
        await session.commit()
        elapsed = time.time() - t0

    print(f"Done in {elapsed:.1f}s.")
    print(f"  documents inserted: {report.documents_inserted}")
    print(f"  chunks inserted:    {report.chunks_inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Add Makefile target**

Modify [Makefile](../../../Makefile). After the `backend-seed:` block, add:

```makefile
seed-corpus:
	cd backend && $(PY) scripts/seed_corpus.py
```

And add `seed-corpus` to the `.PHONY:` line and the `help:` block. Don't run this yet — wait until Task 23 produces actual corpus files.

- [ ] **Step 3: Commit**

```powershell
git add backend/scripts/seed_corpus.py Makefile
git commit -m "feat(scripts): seed_corpus.py CLI + make seed-corpus target"
```

---

# Phase B.3 — Retrieval

## Task 14: RRF fusion (pure function)

**Files:**
- Create: `backend/app/services/retrieval/__init__.py` (empty marker for now)
- Create: `backend/app/services/retrieval/rrf.py`
- Test: `backend/tests/test_rrf.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_rrf.py](../../../backend/tests/test_rrf.py):

```python
from app.services.retrieval.rrf import rrf_fuse


def test_fuses_single_list():
    bm = [("a", 1), ("b", 2), ("c", 3)]
    vec = []
    fused = rrf_fuse(bm, vec, k=60)
    assert [x[0] for x in fused] == ["a", "b", "c"]


def test_boosts_items_in_both_lists():
    bm = [("a", 1), ("b", 2), ("c", 3)]
    vec = [("b", 1), ("a", 2), ("d", 3)]
    fused = rrf_fuse(bm, vec, k=60)
    # a and b appear in both → should rank above c and d which appear in one
    ranking = [x[0] for x in fused]
    assert set(ranking[:2]) == {"a", "b"}


def test_higher_rank_wins_tie():
    bm = [("a", 1), ("b", 2)]
    vec = [("b", 1), ("a", 2)]
    fused = rrf_fuse(bm, vec, k=60)
    # both appear once at rank 1 and once at rank 2 → tied score; preserve a stable order
    assert {x[0] for x in fused} == {"a", "b"}


def test_score_decreases_with_rank():
    bm = [("a", 1), ("b", 2), ("c", 3), ("d", 4)]
    vec = []
    fused = rrf_fuse(bm, vec, k=60)
    scores = [x[1] for x in fused]
    assert scores == sorted(scores, reverse=True)


def test_empty_inputs_returns_empty():
    assert rrf_fuse([], [], k=60) == []
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_rrf.py -v
```

- [ ] **Step 3: Implement**

Create the marker:

```powershell
ni backend/app/services/retrieval/__init__.py -ItemType File
```

Create [backend/app/services/retrieval/rrf.py](../../../backend/app/services/retrieval/rrf.py):

```python
from __future__ import annotations

from typing import Hashable, Sequence, TypeVar

T = TypeVar("T", bound=Hashable)


def rrf_fuse(
    list_a: Sequence[tuple[T, int]],
    list_b: Sequence[tuple[T, int]],
    *,
    k: int = 60,
) -> list[tuple[T, float]]:
    """Reciprocal Rank Fusion.

    Each input is `[(item_id, rank)]` where rank starts at 1. Score per item =
    sum over lists of `1 / (k + rank)`. Returns items sorted by descending score.
    """
    scores: dict[T, float] = {}
    for ranked in (list_a, list_b):
        for item_id, rank in ranked:
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_rrf.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 77 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/retrieval/__init__.py backend/app/services/retrieval/rrf.py backend/tests/test_rrf.py
git commit -m "feat(retrieval): RRF fusion (pure function)"
```

---

## Task 15: Refusal — ref ID + audit insert

**Files:**
- Create: `backend/app/services/retrieval/refusal.py`
- Test: `backend/tests/test_refusal.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_refusal.py](../../../backend/tests/test_refusal.py):

```python
import re
import uuid

import pytest
from sqlalchemy import select

from app.domain.models import AuditEvent
from app.repositories.audit_repository import AuditRepository
from app.services.retrieval.refusal import generate_reference_id, record_refusal


def test_reference_id_format():
    ref = generate_reference_id()
    assert re.fullmatch(r"[A-Z2-7]{4}-[A-Z2-7]{4}", ref)


def test_reference_id_is_random():
    ids = {generate_reference_id() for _ in range(50)}
    assert len(ids) > 45  # tolerate astronomically unlikely collision


@pytest.mark.asyncio
async def test_record_refusal_persists_audit_row(db_session, empire_tenant):
    audit = AuditRepository(db_session)
    user = uuid.uuid4()
    withheld = [uuid.uuid4(), uuid.uuid4()]
    ref = await record_refusal(
        audit,
        tenant_id=empire_tenant.id,
        user_id=user,
        retrieved_ids=[],
        withheld_ids=withheld,
    )
    await db_session.flush()
    assert re.fullmatch(r"[A-Z2-7]{4}-[A-Z2-7]{4}", ref)

    rows = (await db_session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    assert rows[0].refusal_ref == ref
    assert rows[0].withheld_ids == withheld
```

- [ ] **Step 2: Run; expect ImportError**

```powershell
python -m pytest tests/test_refusal.py -v
```

- [ ] **Step 3: Implement**

Create [backend/app/services/retrieval/refusal.py](../../../backend/app/services/retrieval/refusal.py):

```python
from __future__ import annotations

import secrets
import uuid
from typing import Sequence

from app.repositories.audit_repository import AuditRepository

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # Crockford-ish base32, no 0/1/8/9


def generate_reference_id() -> str:
    """Eight base32 chars in two hyphenated groups, e.g. 'A7F2-CXJK'."""
    chars = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"{chars[:4]}-{chars[4:]}"


async def record_refusal(
    audit: AuditRepository,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    retrieved_ids: Sequence[uuid.UUID],
    withheld_ids: Sequence[uuid.UUID],
) -> str:
    ref = generate_reference_id()
    await audit.insert_refusal(
        tenant_id=tenant_id,
        user_id=user_id,
        reference_id=ref,
        retrieved_ids=retrieved_ids,
        withheld_ids=withheld_ids,
    )
    return ref
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_refusal.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 80 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/retrieval/refusal.py backend/tests/test_refusal.py
git commit -m "feat(retrieval): refusal ref-id generator + audit recorder"
```

---

## Task 16: `retrieval.search()` — top-level service orchestration

**Files:**
- Modify: `backend/app/services/retrieval/__init__.py`
- Test: `backend/tests/test_retrieval_service.py`

- [ ] **Step 1: Write the failing tests**

Create [backend/tests/test_retrieval_service.py](../../../backend/tests/test_retrieval_service.py):

```python
import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app.core.clearance import ClearanceContext
from app.domain.models import AuditEvent, Chunk, Document
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.retrieval import search


async def _seed(
    session, tenant_id, *, text, classification, department, embedder
):
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    session.add(
        Document(
            id=doc_id, tenant_id=tenant_id, title=f"doc {text[:10]}",
            source_uri=f"corpus/{department}/x.md", classification=classification,
            department=department, version="1", effective_date=dt.date(2020, 1, 1),
            lineage_id=lineage,
        )
    )
    session.add(
        Chunk(
            id=uuid.uuid4(), tenant_id=tenant_id, document_id=doc_id, ordinal=0,
            text_=text, embedding=embedder.embed_one(text).tolist(),
            classification=classification, department=department,
            effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
        )
    )
    await session.flush()
    return doc_id


def _ctx(tenant_id, max_clearance, departments, user_id=None):
    return ClearanceContext(
        tenant_id=tenant_id,
        user_id=user_id or uuid.uuid4(),
        max_clearance=max_clearance,
        departments=tuple(departments),
    )


@pytest.mark.asyncio
async def test_search_returns_only_allowed_results(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="dress code applies to all imperial personnel",
                classification="public", department="hr", embedder=fake)
    await _seed(db_session, empire_tenant.id, text="executive dress code exception protocols",
                classification="secret", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    response = await search(
        session=db_session, ctx=ctx, embedder=fake, query="dress code", top_k=6
    )
    assert all(r.classification == "public" for r in response.results)
    # one higher-clearance hit was withheld → refusal block populated
    assert response.refusal is not None
    assert response.refusal.withheld_count >= 1


@pytest.mark.asyncio
async def test_search_no_refusal_when_executive(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="dress code applies to all imperial personnel",
                classification="public", department="hr", embedder=fake)
    await _seed(db_session, empire_tenant.id, text="executive dress code exception protocols",
                classification="secret", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "top_secret", ["hr"])
    response = await search(
        session=db_session, ctx=ctx, embedder=fake, query="dress code", top_k=6
    )
    assert len(response.results) >= 2
    assert response.refusal is None


@pytest.mark.asyncio
async def test_search_writes_query_audit_row(db_session, empire_tenant):
    fake = FakeEmbeddingProvider()
    await _seed(db_session, empire_tenant.id, text="public chunk",
                classification="public", department="hr", embedder=fake)

    ctx = _ctx(empire_tenant.id, "public", ["hr"])
    await search(session=db_session, ctx=ctx, embedder=fake, query="public", top_k=6)
    await db_session.flush()

    rows = (await db_session.execute(select(AuditEvent).where(AuditEvent.event_type == "query"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].query_text == "public"
```

- [ ] **Step 2: Run; expect ImportError on `search`**

```powershell
python -m pytest tests/test_retrieval_service.py -v
```

- [ ] **Step 3: Implement**

Replace [backend/app/services/retrieval/__init__.py](../../../backend/app/services/retrieval/__init__.py) with:

```python
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clearance import ClearanceContext
from app.domain.chunk import RefusalContext, RetrievalResult, SearchResponse
from app.repositories.audit_repository import AuditRepository
from app.repositories.chunk_repository import ChunkHit, ChunkRepository
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.retrieval.refusal import record_refusal
from app.services.retrieval.rrf import rrf_fuse

CANDIDATES_PER_BRANCH = 25


async def search(
    *,
    session: AsyncSession,
    ctx: ClearanceContext,
    embedder: EmbeddingProvider,
    query: str,
    top_k: int = 6,
) -> SearchResponse:
    if not query.strip():
        raise ValueError("query must be non-empty")

    chunk_repo = ChunkRepository(session)
    audit = AuditRepository(session)

    query_vec = embedder.embed_one(query).tolist()

    bm_task = chunk_repo.bm25_topn(ctx, query=query, n=CANDIDATES_PER_BRANCH)
    vec_task = chunk_repo.vector_topn(ctx, query_vector=query_vec, n=CANDIDATES_PER_BRANCH)
    unfiltered_task = chunk_repo.unfiltered_topn_ids(
        tenant_id=ctx.tenant_id, query=query, query_vector=query_vec, n=CANDIDATES_PER_BRANCH
    )
    bm_hits, vec_hits, unfiltered_ids = await asyncio.gather(bm_task, vec_task, unfiltered_task)

    fused = rrf_fuse(
        [(h.chunk_id, h.rank) for h in bm_hits],
        [(h.chunk_id, h.rank) for h in vec_hits],
        k=60,
    )

    by_id: dict = {h.chunk_id: h for h in bm_hits}
    for h in vec_hits:
        by_id.setdefault(h.chunk_id, h)

    results: list[RetrievalResult] = []
    for fused_rank, (chunk_id, score) in enumerate(fused[:top_k], start=1):
        h: ChunkHit = by_id[chunk_id]
        results.append(
            RetrievalResult(
                chunk_id=h.chunk_id, document_id=h.document_id,
                document_title=h.document_title, classification=h.classification,
                department=h.department, effective_date=h.effective_date,
                snippet=h.snippet, score=score, rank=fused_rank,
            )
        )

    filtered_ids = set(by_id.keys())
    withheld_ids = list(unfiltered_ids - filtered_ids)

    refusal: RefusalContext | None = None
    retrieved_for_audit = [r.chunk_id for r in results]
    if withheld_ids:
        ref = await record_refusal(
            audit,
            tenant_id=ctx.tenant_id, user_id=ctx.user_id,
            retrieved_ids=retrieved_for_audit, withheld_ids=withheld_ids,
        )
        refusal = RefusalContext(
            reference_id=ref, withheld_count=len(withheld_ids),
            withheld_ids=tuple(withheld_ids),
        )

    await audit.insert_query(
        tenant_id=ctx.tenant_id, user_id=ctx.user_id,
        query_text=query, retrieved_ids=retrieved_for_audit,
    )

    return SearchResponse(results=tuple(results), refusal=refusal)
```

- [ ] **Step 4: Run; expect green**

```powershell
python -m pytest tests/test_retrieval_service.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Full suite green**

```powershell
python -m pytest -v
```

Expected: 83 tests pass. Total runtime should still be under 15 s.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/retrieval/__init__.py backend/tests/test_retrieval_service.py
git commit -m "feat(retrieval): top-level search() with hybrid + RRF + refusal counting"
```

---

# Phase B.4 — API endpoint

## Task 17: API schemas for `POST /retrieval/search`

**Files:**
- Modify: `backend/app/api/schemas.py`

- [ ] **Step 1: Add request/response models**

Append to [backend/app/api/schemas.py](../../../backend/app/api/schemas.py):

```python
import datetime as dt


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    score: float
    rank: int


class RefusalSummary(BaseModel):
    withheld_count: int
    reference_id: str


class SearchResponseBody(BaseModel):
    results: list[SearchResultItem]
    refusal: RefusalSummary | None = None
```

- [ ] **Step 2: Full suite green** (no new tests; schemas are exercised by Task 18 tests)

```powershell
python -m pytest -v
```

Expected: 83 tests pass.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/api/schemas.py
git commit -m "feat(api): add retrieval search request/response schemas"
```

---

## Task 18: `POST /retrieval/search` router + wire into app

The router needs an `EmbeddingProvider` dependency. Production uses BGE (singleton via `lru_cache`); tests override the dependency to use the fake.

**Files:**
- Create: `backend/app/api/retrieval.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/services/ingestion/embedding_factory.py`
- Test: `backend/tests/test_retrieval_api.py`

- [ ] **Step 1: Implement the embedding factory (cached singleton)**

Create [backend/app/services/ingestion/embedding_factory.py](../../../backend/app/services/ingestion/embedding_factory.py):

```python
from __future__ import annotations

from functools import lru_cache

from app.services.ingestion.embedding import BgeEmbeddingProvider, EmbeddingProvider


@lru_cache
def get_default_embedder() -> EmbeddingProvider:
    """Cached singleton — the BGE model loads once per process."""
    return BgeEmbeddingProvider()
```

- [ ] **Step 2: Write the failing API tests**

Create [backend/tests/test_retrieval_api.py](../../../backend/tests/test_retrieval_api.py):

```python
import datetime as dt
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Chunk, Document, User
from app.main import app
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder


@pytest_asyncio.fixture
async def client(db_session):
    from app.core.database import get_session

    async def _override_session():
        yield db_session

    fake = FakeEmbeddingProvider()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_default_embedder] = lambda: fake
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_user_and_chunks(
    db_session, empire_tenant, *, username, role, max_clearance, departments, chunks,
):
    user = User(
        id=uuid.uuid4(), tenant_id=empire_tenant.id, username=username,
        password_hash=hash_password("imperial-march"),
        role=role.value, max_clearance=max_clearance.value, departments=departments,
    )
    db_session.add(user)
    fake = FakeEmbeddingProvider()
    for text, classification, department in chunks:
        doc_id = uuid.uuid4()
        lineage = uuid.uuid4()
        db_session.add(
            Document(
                id=doc_id, tenant_id=empire_tenant.id, title=f"doc {text[:10]}",
                source_uri=f"corpus/{department}/x.md", classification=classification,
                department=department, version="1.0",
                effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
            )
        )
        db_session.add(
            Chunk(
                id=uuid.uuid4(), tenant_id=empire_tenant.id, document_id=doc_id,
                ordinal=0, text_=text, embedding=fake.embed_one(text).tolist(),
                classification=classification, department=department,
                effective_date=dt.date(2020, 1, 1), lineage_id=lineage,
            )
        )
    await db_session.flush()
    return user


async def _login(client, empire_tenant, username):
    return await client.post(
        "/auth/login",
        json={"tenant_id": str(empire_tenant.id), "username": username, "password": "imperial-march"},
    )


@pytest.mark.asyncio
async def test_search_unauthenticated_returns_401(client):
    resp = await client.post("/retrieval/search", json={"query": "anything"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query_returns_422(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="employee.security", role=Role.EMPLOYEE,
        max_clearance=ClearanceLevel.PUBLIC, departments=["security"],
        chunks=[("anything", "public", "security")],
    )
    await _login(client, empire_tenant, "employee.security")
    resp = await client.post("/retrieval/search", json={"query": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_employee_sees_public_only_and_gets_refusal(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="employee.security", role=Role.EMPLOYEE,
        max_clearance=ClearanceLevel.PUBLIC, departments=["security"],
        chunks=[
            ("dress code applies to all imperial personnel", "public", "hr"),
            ("executive dress code exception protocols", "secret", "hr"),
        ],
    )
    await _login(client, empire_tenant, "employee.security")
    resp = await client.post("/retrieval/search", json={"query": "dress code"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(r["classification"] == "public" for r in body["results"])
    assert body["refusal"] is not None
    assert body["refusal"]["withheld_count"] >= 1
    assert "-" in body["refusal"]["reference_id"]


@pytest.mark.asyncio
async def test_search_executive_no_refusal(client, empire_tenant, db_session):
    await _make_user_and_chunks(
        db_session, empire_tenant, username="executive.fleet", role=Role.EXECUTIVE,
        max_clearance=ClearanceLevel.TOP_SECRET, departments=["fleet_operations", "security", "hr"],
        chunks=[
            ("dress code applies to all imperial personnel", "public", "hr"),
            ("executive dress code exception protocols", "secret", "hr"),
        ],
    )
    await _login(client, empire_tenant, "executive.fleet")
    resp = await client.post("/retrieval/search", json={"query": "dress code"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) >= 2
    assert body["refusal"] is None
```

- [ ] **Step 3: Run; expect 404 or ImportError**

```powershell
python -m pytest tests/test_retrieval_api.py -v
```

- [ ] **Step 4: Implement the router**

Create [backend/app/api/retrieval.py](../../../backend/app/api/retrieval.py):

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import RefusalSummary, SearchRequest, SearchResponseBody, SearchResultItem
from app.core.clearance import ClearanceContext
from app.core.database import get_session
from app.core.tenant import get_tenant_context
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder
from app.services.retrieval import search

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=SearchResponseBody)
async def post_search(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
    tenant_ctx=Depends(get_tenant_context),
    embedder: EmbeddingProvider = Depends(get_default_embedder),
) -> SearchResponseBody:
    ctx = ClearanceContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        max_clearance=tenant_ctx.max_clearance,
        departments=tuple(tenant_ctx.departments),
    )
    response = await search(
        session=session, ctx=ctx, embedder=embedder,
        query=body.query, top_k=body.top_k,
    )
    return SearchResponseBody(
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id, document_id=r.document_id,
                document_title=r.document_title, classification=r.classification,
                department=r.department, effective_date=r.effective_date,
                snippet=r.snippet, score=r.score, rank=r.rank,
            )
            for r in response.results
        ],
        refusal=(
            RefusalSummary(
                withheld_count=response.refusal.withheld_count,
                reference_id=response.refusal.reference_id,
            )
            if response.refusal else None
        ),
    )
```

- [ ] **Step 5: Wire the router into `main.py`**

In [backend/app/main.py](../../../backend/app/main.py), add the import + include:

```python
from app.api.retrieval import router as retrieval_router
# ...
app.include_router(retrieval_router)
```

- [ ] **Step 6: Run API tests; expect green**

```powershell
python -m pytest tests/test_retrieval_api.py -v
```

Expected: 4 tests pass.

- [ ] **Step 7: Full suite green**

```powershell
python -m pytest -v
```

Expected: 87 tests pass. Runtime under 15 s.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/api/retrieval.py backend/app/main.py backend/app/services/ingestion/embedding_factory.py backend/tests/test_retrieval_api.py
git commit -m "feat(api): POST /retrieval/search with clearance-aware filtering"
```

---

# Phase B.5 — Corpus

## Task 19: Round 1 — author the 4 voice-calibration documents

These four documents establish the corporate-enterprise voice. Lutfi reviews and edits.

**Files (all NEW):**
- `corpus/hr/employee_handbook_2019.md`
- `corpus/hr/management_conduct_supplement_2023.md`
- `corpus/engineering/reactor_operations_manual_2019.md`
- `corpus/engineering/reactor_operations_manual_2023.md`

**Voice guardrails (re-stated for the executing agent):**
- Read like real internal corporate policies.
- Sections, bullet lists, "Approved by" footer, revision history block.
- No dramatic prose. Star Wars flavor lives in **proper nouns** (Death Star, Coruscant, Stardate) and approver names — never in narrative tone.
- Length: 600–1500 words per doc.
- Seeded conflicts must be **mechanical and direct** so the LLM-as-judge (Phase C) catches them.

### Seeded conflicts to plant

| Conflict | Doc A says | Doc B says |
|---|---|---|
| Demo A (dress code) | `employee_handbook_2019.md`: "Off-duty personnel may display unit insignia on personal attire at sanctioned events." | `management_conduct_supplement_2023.md`: "Off-duty personnel of Manager rank and above must NOT display unit insignia on personal attire, including at sanctioned events." |
| Demo B (reactor shutdown sequence) | `reactor_operations_manual_2019.md`: shutdown sequence is **Coolant Loop A → Coolant Loop B → Magnetic Containment** | `reactor_operations_manual_2023.md`: shutdown sequence is **Magnetic Containment → Coolant Loop B → Coolant Loop A** |

- [ ] **Step 1: Draft `corpus/hr/employee_handbook_2019.md`**

Create the file with:

```markdown
---
title: Imperial Employee Handbook
classification: public
department: hr
version: "3.1"
effective_date: 2019-04-12
lineage_id: employee-handbook
---

# Imperial Employee Handbook

## 1. Purpose and Scope

This Handbook establishes the standards of conduct, presentation, and
professional behavior expected of all Imperial personnel across every garrison,
installation, and vessel. It applies to all rank tiers below the threshold of
Manager unless explicitly stated otherwise. Where a higher-tier policy is in
effect, this Handbook is superseded only for the affected provisions.

## 2. Hours of Service and Leave

Standard duty cycles are 8 standard hours per shift, with a maximum of two
consecutive shifts permitted only under operational directive. Personnel
accrue 2.5 days of compensated leave per standard month and may carry forward
up to 30 days into the subsequent fiscal year. Requests for leave must be
filed with the personnel office no fewer than 14 standard days in advance,
except in cases of bereavement or medical emergency.

## 3. Personal Conduct

Personnel are expected to maintain decorum consistent with their role as
representatives of the Imperial Service. Conduct unbecoming — including but
not limited to public intoxication while in uniform, fraternization with
personnel of conflicting chain of command, and disparagement of Imperial
policy in public-facing settings — is grounds for disciplinary review.

## 4. Dress Code and Insignia

The standard duty uniform is required during all on-base activities. Off-duty
attire is at the discretion of the individual provided it does not bring the
Service into disrepute.

**Off-duty insignia.** Off-duty personnel may display unit insignia on
personal attire at sanctioned off-base events. This includes garrison patches,
unit pins, and standard-issue rank devices worn on civilian outerwear.

Sanctioned off-base events include unit reunions, retirement ceremonies,
recruitment fairs, and official Imperial Service Days.

## 5. Workplace Safety

All personnel must report unsafe conditions to their immediate supervisor
within one duty cycle of discovery. Personal protective equipment is required
in designated areas. Failure to wear PPE in a designated area is grounds for
immediate removal from the work site pending review.

## 6. Confidentiality

Information classified Restricted or higher must not be discussed in any
setting accessible to personnel without the corresponding clearance.
Personnel are reminded that classification levels are enforced both
administratively and technically; circumvention attempts are subject to
review by the Office of Internal Security.

## 7. Grievance Procedure

Personnel may file grievances through their immediate supervisor or, where
the grievance pertains to the supervisor themselves, through the next level
of command. The Office of Personnel Affairs maintains an independent review
channel for grievances that cannot be resolved at the local level.

## 8. Compensation and Benefits

Base compensation is set by rank tier and adjusted annually by the Office of
Compensation. Benefits include medical coverage at any Imperial medical
facility, family transit allowances for personnel stationed off-world, and
retirement contributions managed through the Imperial Service Pension Fund.

## 9. Termination and Separation

Voluntary separation requires 30 standard days of notice. Involuntary
separation follows the procedure set out in the Personnel Disciplinary Code
and may be appealed within 14 standard days of issuance.

---

**Approved by:** Director of Personnel Affairs, Mira Vellance
**Effective:** Stardate 7472.12 / 2019-04-12
**Supersedes:** Imperial Employee Handbook v3.0 (2017-09-01)
**Next scheduled review:** 2024-04-12
```

- [ ] **Step 2: Draft `corpus/hr/management_conduct_supplement_2023.md`**

```markdown
---
title: Management Conduct Supplement
classification: restricted
department: hr
version: "1.0"
effective_date: 2023-11-01
lineage_id: employee-handbook
---

# Management Conduct Supplement

## 1. Purpose

This Supplement extends the Imperial Employee Handbook with provisions
applicable to personnel of Manager rank and above. Where a provision of this
Supplement conflicts with the Handbook, this Supplement governs for the
affected personnel.

## 2. Public Representation

Managers, Directors, and Executives are public-facing representatives of the
Service and are subject to heightened standards regarding off-duty
appearance, public statements, and association with non-Imperial entities.

## 3. Dress Code Override

**Off-duty insignia restriction.** Off-duty personnel of Manager rank and
above must NOT display unit insignia on personal attire, including at
sanctioned events. This restriction applies to garrison patches, unit pins,
rank devices, and any item identifying the wearer's unit or command.

Rationale: Manager-tier personnel are personally identifiable in public
intelligence assessments. Insignia display at recurring public events
materially increases pattern-of-life exposure for the wearer and their
command.

This provision supersedes Section 4 of the Imperial Employee Handbook
(v3.1, 2019) for personnel within its scope.

## 4. Off-Site Conduct

Off-site meetings with non-Imperial personnel, including former Service
members, must be reported to the Office of Personnel Affairs within 72
standard hours of occurrence. Casual social encounters of less than 30
standard minutes are exempt.

## 5. Discretionary Spending Authority

Managers retain discretionary spending authority up to 25,000 credits per
fiscal quarter without further approval. Expenditures exceeding this
threshold require concurrence from the next level of command.

## 6. Subordinate Performance Reviews

Performance reviews of direct subordinates must be conducted no less
frequently than semi-annually. Reviews must be documented in the personnel
information system within 14 standard days of completion.

## 7. Disciplinary Authority

Managers are authorized to issue written reprimands and to recommend
suspension. Termination authority remains with Directors and above.

## 8. Confidentiality Reaffirmation

Manager-tier personnel routinely handle information classified Restricted.
The standard non-disclosure provisions of the Handbook apply; in addition,
managers must refresh their classification training annually.

---

**Approved by:** Director of Personnel Affairs, Mira Vellance
**Effective:** Stardate 7891.04 / 2023-11-01
**Supersedes:** Section 4 of Imperial Employee Handbook v3.1 (insignia provisions)
**Next scheduled review:** 2026-11-01
```

- [ ] **Step 3: Draft `corpus/engineering/reactor_operations_manual_2019.md`**

```markdown
---
title: Reactor Operations Manual
classification: restricted
department: engineering
version: "2.0"
effective_date: 2019-08-15
lineage_id: reactor-manual
---

# Reactor Operations Manual

## 1. Scope

This Manual covers normal operation, controlled shutdown, and emergency
shutdown of the Class-IV hyperreactor systems deployed on capital-scale
installations, including but not limited to the Death Star primary reactor
core and the Star Destroyer-class power plants.

## 2. Operating Parameters

Nominal operating temperature is 1.2 million Kelvin at the containment
boundary. Core throughput is regulated by the magnetic containment field;
secondary regulation is provided by coolant loops A and B operating in
parallel.

Coolant flow rates: Loop A at 47,000 L/s, Loop B at 47,000 L/s. Both loops
must be at nominal flow before reactor lift to operating temperature.

## 3. Pre-Start Checklist

Engineering crews must verify the following before reactor lift:

- Containment field integrity at 99.7% or above
- Coolant Loop A pressure within tolerance
- Coolant Loop B pressure within tolerance
- Auxiliary capacitor banks fully charged
- Emergency vent paths confirmed clear

## 4. Normal Shutdown Sequence

Normal shutdown is a controlled three-phase procedure. The phases must be
executed strictly in order. Skipping or reordering a phase will trigger
emergency containment and require post-incident review.

**Phase 1: Coolant Loop A wind-down.** Reduce Loop A flow from nominal to
12,000 L/s over a span of no less than 60 standard seconds. Verify
temperature at the containment boundary remains within tolerance.

**Phase 2: Coolant Loop B wind-down.** Reduce Loop B flow from nominal to
8,000 L/s over a span of no less than 90 standard seconds. Coolant Loop A
must remain at the Phase 1 setpoint throughout.

**Phase 3: Magnetic containment release.** Reduce the magnetic containment
field strength from 99.7% to 5% over a span of no less than 120 standard
seconds. The reactor will enter low-output standby. Final disengagement of
containment is performed only after temperature falls below 200,000 K.

The complete shutdown sequence is therefore:
**Coolant Loop A → Coolant Loop B → Magnetic Containment.**

## 5. Emergency Shutdown

Emergency shutdown bypasses Phase 1 and Phase 2. Magnetic containment is
released at the maximum sustainable rate; coolant loops are slammed to
emergency-vent settings. Use of emergency shutdown requires a post-incident
review board within 14 standard days.

## 6. Post-Shutdown Inspection

A full containment-boundary inspection is required within 6 standard hours
of any shutdown. Inspection results are filed with the Department of
Engineering and copied to the Office of Internal Security.

---

**Approved by:** Chief Engineering Officer, Renn Korso
**Effective:** Stardate 7501.22 / 2019-08-15
**Supersedes:** Reactor Operations Manual v1.4 (2014-03-01)
**Next scheduled review:** 2024-08-15
```

- [ ] **Step 4: Draft `corpus/engineering/reactor_operations_manual_2023.md`**

```markdown
---
title: Reactor Operations Manual (Amended)
classification: restricted
department: engineering
version: "2.3"
effective_date: 2023-02-09
lineage_id: reactor-manual
---

# Reactor Operations Manual (Amended)

## 1. Scope

This amended Manual supersedes Reactor Operations Manual v2.0 (2019-08-15)
for all Class-IV hyperreactor systems. Engineering crews must complete the
amended-procedure certification within 90 standard days of the effective
date.

## 2. Operating Parameters

Nominal operating temperature is 1.2 million Kelvin at the containment
boundary. Coolant flow rates remain unchanged: Loop A at 47,000 L/s, Loop B
at 47,000 L/s, both at nominal before reactor lift.

## 3. Pre-Start Checklist

Pre-start verification is unchanged from v2.0. See Section 3 of the prior
revision.

## 4. Normal Shutdown Sequence — REVISED

Investigation of the 2022 Carida III incident determined that progressive
coolant wind-down prior to magnetic containment release places anomalous
stress on the containment boundary during low-output transitions. The
shutdown sequence is therefore revised.

The amended shutdown sequence is:

**Phase 1: Magnetic containment step-down.** Reduce magnetic containment
field strength from 99.7% to 60% over a span of no less than 90 standard
seconds. Coolant loops remain at nominal throughout.

**Phase 2: Coolant Loop B wind-down.** Reduce Loop B flow from nominal to
8,000 L/s over a span of no less than 60 standard seconds. Containment
field remains at the Phase 1 setpoint.

**Phase 3: Coolant Loop A wind-down.** Reduce Loop A flow from nominal to
12,000 L/s over a span of no less than 60 standard seconds. Magnetic
containment is then released to 5% over a final 60 standard seconds.

The complete revised shutdown sequence is therefore:
**Magnetic Containment → Coolant Loop B → Coolant Loop A.**

This sequence directly supersedes the procedure in Reactor Operations Manual
v2.0 Section 4. Use of the v2.0 sequence after the effective date of this
amendment is a reportable engineering deviation.

## 5. Emergency Shutdown

Emergency shutdown procedures are unchanged from v2.0.

## 6. Certification Requirements

All certified reactor operators must re-certify on the amended sequence
within 90 standard days. Re-certification consists of a written examination
and three supervised simulator runs at the amended sequence.

---

**Approved by:** Chief Engineering Officer, Renn Korso
**Co-approved by:** Director of Engineering, Tarin Vex
**Effective:** Stardate 7842.19 / 2023-02-09
**Supersedes:** Section 4 of Reactor Operations Manual v2.0
**Next scheduled review:** 2026-02-09
```

- [ ] **Step 5: Voice review checkpoint**

**This is a human-review step.** Stop and request review from Lutfi:

> "Round 1 corpus drafts written (4 docs). Please skim for tone, voice, and structure. Round 2 (~12 more docs) will be batched off whatever you approve. Edits requested?"

Wait for approval or revisions. Iterate as needed.

- [ ] **Step 6: Commit Round 1 (after voice approval)**

```powershell
git add corpus/
git commit -m "corpus: round 1 voice-calibration docs (handbook+supplement, reactor manual pair)"
```

---

## Task 20: Round 2 — author the remaining ~12 documents

After voice approval, generate the rest in three directory-grouped batches. Each document follows the same structure (sections, bullets, "Approved by" footer, revision history). Document the seeded conflicts as you write.

**Required by spec §6 coverage matrix (see also the spec doc tables):**

### Batch A: HR remaining (~2 docs)

- [ ] `corpus/hr/remote_work_policy_2018.md` — **outdated-but-not-superseded**. Classification: public. Pre-Galactic Civil War language references to "any approved off-world residence" suggest a more permissive era; the document is still officially in force but nobody references it in recent years.
- [ ] `corpus/hr/recruitment_policy_public.md` — Classification: public. Part of the **recruitment ladder** (public → restricted → secret). Surface-level recruitment process; vague on actual selection criteria.

### Batch B: Engineering remaining (~2 docs)

- [ ] `corpus/engineering/safety_thresholds_2022.md` — Classification: restricted, department: engineering. Specifies safe operating thresholds for capital-class vessels. **Plants cross-department conflict**: lists a max-stress-load value that contradicts the Fleet Operations deployment guideline.
- [ ] `corpus/engineering/manager_hiring_guidelines_restricted.md` — Classification: restricted. Part of the **recruitment ladder**. Engineering-specific manager hiring criteria including technical assessments and clearance pre-screening.

### Batch C: Fleet Ops (~3 docs)

- [ ] `corpus/fleet_ops/deployment_thresholds_2023.md` — Classification: restricted, department: fleet_operations. **Cross-department conflict counterpart**: max-stress-load value that disagrees with the engineering safety threshold by ~15%. Phase C conflict detection will surface this pairing.
- [ ] `corpus/fleet_ops/sector_assignment_policy.md` — Classification: restricted, department: fleet_operations. Routine fleet posting policy.
- [ ] `corpus/fleet_ops/executive_search_protocol_top_secret.md` — Classification: top_secret. Top of the **executive search ladder**. Final-tier vetting protocol for senior command appointments.

### Batch D: Security (~3 docs)

- [ ] `corpus/security/access_audit_policy_2023.md` — Classification: restricted, department: security. **Plants cross-department conflict**: specifies quarterly access audits.
- [ ] `corpus/security/onboarding_audit_policy_2023.md` — Classification: restricted, department: hr. **Conflict counterpart**: specifies annual access audits for new hires (vs Security's quarterly cadence). Note: this doc lives under `corpus/security/` for filesystem grouping but its `department` field is `hr` — this is intentional to create the cross-department mismatch.
  - **Correction:** make it `corpus/hr/onboarding_audit_policy_2023.md` and keep its department as `hr`. The HR/Security audit cadence mismatch IS the cross-dept conflict.
- [ ] `corpus/security/executive_search_secret.md` — Classification: secret. Middle tier of the **executive search ladder**.

### Batch E: Procurement (~2 docs)

- [ ] `corpus/procurement/procurement_policy_2020.md` — Classification: restricted, department: procurement. **Lineage pair partner**. Vendor approval thresholds.
- [ ] `corpus/procurement/procurement_policy_2024.md` — Classification: restricted, department: procurement. **Lineage pair partner** with conflict: revised vendor approval thresholds (e.g., authority limit changes from 100,000 credits to 250,000 credits).

### Final count check

- hr: handbook (1), supplement (2), remote_work (3), recruitment (4), onboarding_audit (5) — recount expected: 4. Drop `onboarding_audit` to the count? Actually re-check spec target: hr ×4 in the design. So drop one. Removing `recruitment_policy_public` — keep the recruitment ladder anchored on `manager_hiring_guidelines_restricted` (engineering) and skip the public-tier recruitment doc.
- engineering: reactor_2019 (1), reactor_2023 (2), safety_thresholds (3), manager_hiring_guidelines (4) → 4 ✓
- hr: handbook (1), supplement (2), remote_work (3), onboarding_audit (4) → 4 ✓
- fleet_ops: deployment_thresholds (1), sector_assignment (2), executive_search_top_secret (3) → 3 ✓
- security: access_audit (1), executive_search_secret (2) → revise to 3 by adding `corpus/security/insider_threat_assessment.md` (Classification: secret, department: security) → 3 ✓
- procurement: 2020 (1), 2024 (2) → 2 ✓

**Total: 16 documents.** Matches the design target.

- [ ] **Step 1: Write Batch A (hr remaining: remote_work_2018, onboarding_audit_2023)**

For each file: same structure as Round 1 — frontmatter, sections, bullets, footer with Approved by + effective date + supersedes + next review. Length 600–1500 words. Tone matches Round 1 baseline.

- [ ] **Step 2: Write Batch B (engineering remaining: safety_thresholds_2022, manager_hiring_guidelines_restricted)**

**Critical:** `safety_thresholds_2022.md` MUST include a specific numeric value (e.g., "Maximum hull stress load for Class-II Star Destroyers: 8.4 × 10⁹ Newtons") that the Fleet Ops counterpart contradicts.

- [ ] **Step 3: Write Batch C (fleet_ops: deployment_thresholds_2023, sector_assignment_policy, executive_search_protocol_top_secret)**

`deployment_thresholds_2023.md` MUST include the contradicting number: "Class-II Star Destroyer deployment is authorized at sustained hull stress loads up to 9.7 × 10⁹ Newtons" — a deliberate ~15% disagreement with engineering's safety threshold.

- [ ] **Step 4: Write Batch D (security: access_audit_2023, executive_search_secret, insider_threat_assessment)**

`access_audit_policy_2023.md` MUST state audit cadence as "quarterly" for the dept-conflict pairing.

- [ ] **Step 5: Write Batch E (procurement: 2020, 2024)**

`procurement_policy_2020.md` MUST state Manager-tier approval authority at "100,000 credits per fiscal quarter".
`procurement_policy_2024.md` MUST state it at "250,000 credits per fiscal quarter" — the seeded lineage conflict.

- [ ] **Step 6: Commit Round 2**

```powershell
git add corpus/
git commit -m "corpus: round 2 — 12 documents covering all spec §6 coverage requirements"
```

---

# Phase B.6 — Wire-up + smoke test + polish

## Task 21: End-to-end smoke test against the real corpus

This is the Phase B exit-criteria verification. Not a `pytest` test — a manual / scripted run that proves the end-to-end flow.

**Prerequisite:** Postgres + Redis up via `docker compose up -d postgres redis`. Phase A tenant + users seeded via `make backend-seed`. Run from repo root after `cd backend && .\.venv\Scripts\Activate.ps1`.

- [ ] **Step 1: Run migrations + seed users (if not already)**

```powershell
python -m alembic upgrade head
python scripts/seed_users.py
```

Capture the tenant ID printed in the seed output — needed for login.

- [ ] **Step 2: Run corpus ingest**

```powershell
python scripts/seed_corpus.py
```

Expected output:

```
Loading BGE model (first run downloads ~440 MB)...
Ingesting from .../corpus into tenant <UUID>...
Done in <under 60>s.
  documents inserted: 16
  chunks inserted:    300-500
```

- [ ] **Step 3: Start backend**

In a separate PowerShell window:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 4: Verify the Demo A path (HR / dress code)**

```powershell
# Login as executive.fleet
$tid = "<TENANT_ID_FROM_SEED>"
$session = Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="executive.fleet"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s

# Search as executive — should get both public + restricted
$result = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="dress code policy off-base events" } | ConvertTo-Json) `
  -WebSession $s
$result.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Expected: results include ≥1 chunk from "Imperial Employee Handbook" AND ≥1 chunk from "Management Conduct Supplement". `refusal` is `null`.

- [ ] **Step 5: Repeat as `employee.security` — expect refusal**

```powershell
$session2 = Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="employee.security"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s2

$result2 = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="dress code policy off-base events" } | ConvertTo-Json) `
  -WebSession $s2
$result2.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Expected: results contain ONLY the public Handbook chunk(s). `refusal.withheld_count` ≥ 1. `refusal.reference_id` matches `[A-Z2-7]{4}-[A-Z2-7]{4}`.

- [ ] **Step 6: Verify the audit row exists**

From a third terminal, connect to the DB:

```powershell
docker compose exec postgres psql -U holocron -d holocron -c "SELECT id, event_type, refusal_ref, array_length(withheld_ids, 1) AS n_withheld FROM audit_events WHERE refusal_ref IS NOT NULL ORDER BY id DESC LIMIT 5;"
```

Expected: a row whose `refusal_ref` matches the value returned in Step 5, with `n_withheld` ≥ 1.

- [ ] **Step 7: Verify the Demo B path (engineering / reactor)**

```powershell
# director.engineering — gets both reactor manuals
$session3 = Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="director.engineering"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s3

$result3 = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="reactor shutdown sequence" } | ConvertTo-Json) `
  -WebSession $s3
$result3.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5

# employee.security — no engineering chunks
$session4 = Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="employee.security"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s4

$result4 = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="reactor shutdown sequence" } | ConvertTo-Json) `
  -WebSession $s4
$result4.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Expected: director sees ≥1 chunk from both Reactor Manual versions; security employee sees zero engineering chunks (because reactor docs are `restricted` AND `engineering` department); withheld_count > 0 for the security employee.

- [ ] **Step 8: All exit criteria from the spec verified**

If steps 4–7 produce expected output, Phase B is functionally complete. If any step fails, debug and re-run before proceeding.

- [ ] **Step 9: No commit yet — smoke verification is observational. Move on to documentation.**

---

## Task 22: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Phase B section to the quickstart**

Find the existing quickstart in [README.md](../../../README.md). After the `make backend-seed` step add:

```markdown
5. **Seed the corpus** (one-time; ~30–60 s for first run as BGE model downloads):

   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python scripts/seed_corpus.py
   ```
```

Then add a new "Sample retrieval query" section under the quickstart:

````markdown
### Sample retrieval query

After `seed_corpus.py` completes, with the backend running on port 8000:

```powershell
# Get the tenant ID from `make backend-seed` output
$tid = "<TENANT_ID>"

# Log in as an Imperial Executive (sees everything)
Invoke-WebRequest -Uri http://localhost:8000/auth/login `
  -Method POST -ContentType "application/json" `
  -Body (@{ tenant_id=$tid; username="executive.fleet"; password="imperial-march" } | ConvertTo-Json) `
  -SessionVariable s

# Search
$r = Invoke-WebRequest -Uri http://localhost:8000/retrieval/search `
  -Method POST -ContentType "application/json" `
  -Body (@{ query="dress code policy off-base events" } | ConvertTo-Json) `
  -WebSession $s
$r.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Log in as `employee.security` instead and the same query returns only public results plus a refusal block with a reference ID.
````

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "docs: Phase B README — corpus seed + sample retrieval query"
```

---

## Task 23: Phase B completion record

Mirror the Phase A completion record format.

**Files:**
- Create: `docs/superpowers/plans/2026-06-27-phase-b-ingestion-retrieval-completion.md`

- [ ] **Step 1: Write the record**

Write a short markdown file at the path above with these sections:

- **End-of-phase demo checklist** — each exit criterion from the spec, each checked or noted.
- **Notable plan deviations and why** — at minimum include:
  - SemanticSplitter → SentenceSplitter (Task 11) — quality vs cost tradeoff
  - Spec module layout collapsed `services/retrieval/{bm25,vector}.py` into `ChunkRepository` methods
  - Switched from Gemini to Groq + local BGE — see spec locked decisions
  - Any other deviations encountered during execution
- **Spec coverage** — point each spec section at its implementing task(s).
- **Known follow-ups for Phase C** — entity extraction, conflict detection service, answer generation, frontend chat UI.

- [ ] **Step 2: Commit**

```powershell
git add docs/superpowers/plans/2026-06-27-phase-b-ingestion-retrieval-completion.md
git commit -m "docs: Phase B completion record"
```

---

# Summary

**Total tasks: 23.** Total expected tests after Phase B: **~87** (up from 30). Total runtime target: **under 15 seconds** for the default suite (`-m 'not slow'`).

**Tasks producing observable demo:** Task 21 (smoke test against real corpus) verifies all 8 spec exit criteria.

**Major plan-level refinement of the design:**

1. The design's `services/retrieval/{bm25,vector}.py` modules are collapsed into `ChunkRepository` methods. Repositories own SQL; services orchestrate.
2. The design's `SemanticSplitterNodeParser (sentence fallback)` is implemented as `SentenceSplitter` only in Phase B. Semantic splitting is a Phase C consideration if eval signals demand it.

Both deviations should be re-stated in the completion record (Task 23).
