from __future__ import annotations

import base64
import datetime as _dt
import json
import uuid
from typing import Optional, Sequence

from sqlalchemy import select
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

    async def list_grouped_by_correlation(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int,
        cursor: Optional[str],
        user_id: Optional[uuid.UUID] = None,
        start: Optional[_dt.datetime] = None,
        end: Optional[_dt.datetime] = None,
        has_refusal: Optional[bool] = None,
        has_conflict: Optional[bool] = None,
    ) -> tuple[list[dict], Optional[str]]:
        """Return [{correlation_id, user_id, first_event_at, latency_ms,
        had_refusal, had_conflict, event_count, events:[…]}, …] paged via
        cursor. Demo scale (~1k rows) — server-side GROUP BY in Python is fine."""

        cursor_dt: Optional[_dt.datetime] = None
        cursor_cid: Optional[uuid.UUID] = None
        if cursor:
            decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            cursor_dt = _dt.datetime.fromisoformat(decoded["t"])
            cursor_cid = uuid.UUID(decoded["c"])

        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
        if user_id:
            stmt = stmt.where(AuditEvent.user_id == user_id)
        if start:
            stmt = stmt.where(AuditEvent.created_at >= start)
        if end:
            stmt = stmt.where(AuditEvent.created_at <= end)

        all_events = (await self._session.execute(stmt)).scalars().all()

        groups: dict[uuid.UUID, list[AuditEvent]] = {}
        first_at: dict[uuid.UUID, _dt.datetime] = {}
        for e in all_events:
            groups.setdefault(e.correlation_id, []).append(e)
            if (
                e.correlation_id not in first_at
                or e.created_at < first_at[e.correlation_id]
            ):
                first_at[e.correlation_id] = e.created_at

        sorted_cids = sorted(
            groups.keys(), key=lambda c: (first_at[c], c), reverse=True
        )

        def _has_refusal(events: list[AuditEvent]) -> bool:
            return any(e.event_type == "refusal" for e in events)

        def _has_conflict(events: list[AuditEvent]) -> bool:
            return any(
                e.conflicts_found and (e.conflicts_found.get("count", 0) > 0)
                for e in events
            )

        if has_refusal is True:
            sorted_cids = [c for c in sorted_cids if _has_refusal(groups[c])]
        elif has_refusal is False:
            sorted_cids = [c for c in sorted_cids if not _has_refusal(groups[c])]
        if has_conflict is True:
            sorted_cids = [c for c in sorted_cids if _has_conflict(groups[c])]
        elif has_conflict is False:
            sorted_cids = [c for c in sorted_cids if not _has_conflict(groups[c])]

        if cursor_dt is not None and cursor_cid is not None:
            sorted_cids = [
                c
                for c in sorted_cids
                if (first_at[c], c) < (cursor_dt, cursor_cid)
            ]

        page_cids = sorted_cids[: limit + 1]
        has_more = len(page_cids) > limit
        page_cids = page_cids[:limit]

        rows: list[dict] = []
        for cid in page_cids:
            events = groups[cid]
            latencies = [e.latency_ms for e in events if e.latency_ms is not None]
            user_ids = list({e.user_id for e in events})
            rows.append(
                {
                    "correlation_id": cid,
                    "user_id": user_ids[0] if user_ids else None,
                    "first_event_at": first_at[cid].isoformat(),
                    "latency_ms": max(latencies) if latencies else 0,
                    "had_refusal": _has_refusal(events),
                    "had_conflict": _has_conflict(events),
                    "event_count": len(events),
                    "events": [self._serialize_event(e) for e in events],
                }
            )

        next_cursor = None
        if has_more and page_cids:
            last_cid = page_cids[-1]
            payload = {"t": first_at[last_cid].isoformat(), "c": str(last_cid)}
            next_cursor = base64.urlsafe_b64encode(
                json.dumps(payload).encode()
            ).decode()
        return rows, next_cursor

    async def list_recent_queries(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int,
    ) -> list[dict]:
        """Return the user's last N query events with joined response latency
        (null when the request is still in flight or the response event never
        landed). Newest first."""

        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.user_id == user_id,
                AuditEvent.event_type == "query",
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        query_events = (await self._session.execute(stmt)).scalars().all()
        if not query_events:
            return []

        cids = [e.correlation_id for e in query_events]
        lat_stmt = select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.correlation_id.in_(cids),
            AuditEvent.event_type == "response",
        )
        response_events = (await self._session.execute(lat_stmt)).scalars().all()
        latency_by_cid: dict[uuid.UUID, int | None] = {
            e.correlation_id: e.latency_ms for e in response_events
        }

        return [
            {
                "correlation_id": e.correlation_id,
                "query": e.query_text,
                "occurred_at": e.created_at,
                "latency_ms": latency_by_cid.get(e.correlation_id),
            }
            for e in query_events
        ]

    @staticmethod
    def _serialize_event(e: AuditEvent) -> dict:
        return {
            "event_type": e.event_type,
            "query_text": e.query_text,
            "retrieved_ids": [str(x) for x in (e.retrieved_ids or [])],
            "withheld_ids": [str(x) for x in (e.withheld_ids or [])],
            "refusal_ref": e.refusal_ref,
            "response_text": e.response_text,
            "conflicts_found": e.conflicts_found,
            "latency_ms": e.latency_ms,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
