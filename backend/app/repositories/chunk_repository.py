from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clearance import ClearanceContext, allowed_levels
from app.domain.models import Chunk


@dataclass(frozen=True)
class ChunkHit:
    """A row from BM25 or vector ranking, with all data needed downstream
    (denormalized title pulled in via join). Score semantics: higher == better
    for BM25; for vector branch we convert cosine distance to similarity
    (1.0 - distance) so higher is always better at the call site. RRF only
    needs rank, not raw score."""

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
    entities: list[str]


class ChunkRepository:
    """Type-level RBAC: every chunk read method requires a ClearanceContext.

    The one explicit RBAC bypass is `unfiltered_topn_ids`, named so it cannot
    be confused with a normal read. It exists solely for refusal counting."""

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
                   c.effective_date, c.text, c.lineage_id, c.entities,
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
                snippet=_snippet(row[6]), score=float(row[9]), rank=i + 1,
                lineage_id=row[7], entities=list(row[8] or []),
            )
            for i, row in enumerate(result.fetchall())
        ]

    async def vector_topn(
        self, ctx: ClearanceContext, *, query_vector: list[float], n: int
    ) -> list[ChunkHit]:
        sql = sql_text(
            """
            SELECT c.id, c.document_id, d.title, c.classification, c.department,
                   c.effective_date, c.text, c.lineage_id, c.entities,
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
                score=1.0 - float(row[9]),  # cosine similarity
                rank=i + 1,
                lineage_id=row[7], entities=list(row[8] or []),
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
