from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.warmup import WarmState
from app.main import app


@pytest.mark.asyncio
async def test_correlation_id_round_trips_when_provided_as_uuid():
    """A valid inbound UUID is preserved and echoed back."""
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)
    supplied = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready", headers={"x-correlation-id": supplied})
    assert resp.headers.get("x-correlation-id") == supplied


@pytest.mark.asyncio
async def test_non_uuid_inbound_id_is_replaced_with_fresh_uuid():
    """Client-supplied free-form strings are rejected to keep audit_events
    (correlation_id UUID NOT NULL) intact when they share the same id."""
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready", headers={"x-correlation-id": "not-a-uuid"})
    cid = resp.headers.get("x-correlation-id")
    assert cid and cid != "not-a-uuid"
    uuid.UUID(cid)  # parses cleanly


@pytest.mark.asyncio
async def test_correlation_id_generated_when_absent():
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    cid = resp.headers.get("x-correlation-id")
    assert cid
    # Generated ids are UUID4 strings — 36 chars with hyphens.
    uuid.UUID(cid)  # raises if not a valid UUID
