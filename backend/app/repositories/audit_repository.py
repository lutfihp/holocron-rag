from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AuditEvent


class AuditRepository:
    """Append-only audit writer. Every insert carries a `correlation_id` that
    groups all events for one logical request (typically `/chat/ask`)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_query(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        correlation_id: uuid.UUID,
        query_text: str,
        retrieved_ids: Sequence[uuid.UUID],
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                correlation_id=correlation_id,
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
        correlation_id: uuid.UUID,
        reference_id: str,
        retrieved_ids: Sequence[uuid.UUID],
        withheld_ids: Sequence[uuid.UUID],
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                correlation_id=correlation_id,
                event_type="refusal",
                refusal_ref=reference_id,
                retrieved_ids=list(retrieved_ids),
                withheld_ids=list(withheld_ids),
            )
        )

    async def insert_response(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        correlation_id: uuid.UUID,
        response_text: str,
        conflicts_found: dict | None,
        latency_ms: int,
    ) -> None:
        self._session.add(
            AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                correlation_id=correlation_id,
                event_type="response",
                response_text=response_text,
                conflicts_found=conflicts_found,
                latency_ms=latency_ms,
            )
        )
