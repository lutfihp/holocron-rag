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
