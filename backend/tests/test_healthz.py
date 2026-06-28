from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.warmup import WarmState
from app.main import app


@pytest.mark.asyncio
async def test_healthz_ready_returns_503_when_not_warm():
    app.state.warm = WarmState()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False
    assert body["checks"]["bge"] is False
    assert body["checks"]["spacy"] is False


@pytest.mark.asyncio
async def test_healthz_ready_returns_200_when_bge_and_spacy_warm():
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["checks"]["bge"] is True
    assert body["checks"]["spacy"] is True


@pytest.mark.asyncio
async def test_healthz_ready_groq_does_not_gate_overall_ready():
    """Groq probe is best-effort; its failure must NOT mark the app unready."""
    app.state.warm = WarmState(bge_ready=True, spacy_ready=True, groq_ready=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"]["groq"] is False
