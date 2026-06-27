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
    assert sorted(c.ordinal for c in chunks) == list(range(len(chunks)))
    assert all(c.classification == "public" for c in chunks)
    assert all(c.department == "hr" for c in chunks)


@pytest.mark.asyncio
async def test_ingest_idempotent_via_source_prefix_delete(db_session, empire_tenant, tmp_path):
    corpus = tmp_path / "corpus"
    _write(corpus, "hr/a.md", _basic_doc("Doc A"))
    _write(corpus, "hr/b.md", _basic_doc("Doc B"))

    embedder = FakeEmbeddingProvider()
    r1 = await ingest_corpus_dir(
        corpus, tenant_id=empire_tenant.id, session=db_session, embedder=embedder
    )
    r2 = await ingest_corpus_dir(
        corpus, tenant_id=empire_tenant.id, session=db_session, embedder=embedder
    )
    assert r1.documents_inserted == r2.documents_inserted == 2

    docs = (await db_session.execute(select(Document))).scalars().all()
    assert len(docs) == 2  # NOT 4 — second run replaced first


@pytest.mark.asyncio
async def test_ingest_tenant_scoped(db_session, empire_tenant, tmp_path):
    corpus = tmp_path / "corpus"
    _write(corpus, "hr/a.md", _basic_doc("Doc A"))
    await ingest_corpus_dir(
        corpus, tenant_id=empire_tenant.id, session=db_session, embedder=FakeEmbeddingProvider()
    )

    other_tenant = uuid.uuid4()
    from app.domain.models import Tenant
    db_session.add(Tenant(id=other_tenant, name="Rebel Alliance", role_label_map={}))
    await db_session.flush()
    await ingest_corpus_dir(
        corpus, tenant_id=other_tenant, session=db_session, embedder=FakeEmbeddingProvider()
    )

    docs = (await db_session.execute(select(Document))).scalars().all()
    assert len(docs) == 2  # one per tenant
    tenants_seen = {d.tenant_id for d in docs}
    assert tenants_seen == {empire_tenant.id, other_tenant}
