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

        print("Loading BGE model (first run downloads ~440 MB)...")
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
