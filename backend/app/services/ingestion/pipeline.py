from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chunk, Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion.embedding import EmbeddingProvider
from app.services.ingestion.entity_extractor import extract_entities
from app.services.ingestion.loader import LoadedDocument, load_corpus_dir
from app.services.ingestion.splitter import split_text


@dataclass(frozen=True)
class IngestionReport:
    documents_inserted: int
    chunks_inserted: int


# Stable namespace so identical lineage strings map to identical UUIDs across runs.
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
    tenant, then re-inserts. Default `source_prefix` = '{corpus_dir.name}/'."""

    docs = load_corpus_dir(corpus_dir)
    prefix = source_prefix or f"{corpus_dir.name}/"

    doc_repo = DocumentRepository(session)
    chunk_repo = ChunkRepository(session)

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
            entities=list(extract_entities(text)),
        )
        for i, (text, vec) in enumerate(zip(chunk_texts, vectors))
    ]
    return doc, chunks
