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
