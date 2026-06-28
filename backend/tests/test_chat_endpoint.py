from __future__ import annotations

import datetime as dt
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.core.security import hash_password
from app.domain.enums import ClearanceLevel, Role
from app.domain.models import Chunk, Document, Tenant, User
from app.main import app
from app.services.answer_generation.llm_client import FakeLLMClient, get_default_llm
from app.services.conflict_detection.judge import _judge_cache_clear
from app.services.ingestion.embedding import FakeEmbeddingProvider
from app.services.ingestion.embedding_factory import get_default_embedder


@pytest_asyncio.fixture
async def client(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    app.dependency_overrides[get_default_embedder] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[get_default_llm] = lambda: FakeLLMClient(
        text_responses=["Answer about [1] thing."],
        json_responses=[],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_executive(db_session, empire_tenant: Tenant) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        username="ex-proc",
        password_hash=hash_password("imperial-march"),
        role=Role.EXECUTIVE.value,
        max_clearance=ClearanceLevel.TOP_SECRET.value,
        departments=["procurement", "hr"],
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def seeded_chunk(db_session, empire_tenant: Tenant) -> Chunk:
    fake = FakeEmbeddingProvider()
    doc_id = uuid.uuid4()
    lineage = uuid.uuid4()
    text = "anything about procurement credit thresholds and approvals"
    db_session.add(
        Document(
            id=doc_id,
            tenant_id=empire_tenant.id,
            title="Procurement Policy",
            source_uri="corpus/procurement/policy.md",
            classification="public",
            department="procurement",
            version="1.0",
            effective_date=dt.date(2024, 1, 1),
            lineage_id=lineage,
        )
    )
    await db_session.flush()
    chunk = Chunk(
        id=uuid.uuid4(),
        tenant_id=empire_tenant.id,
        document_id=doc_id,
        ordinal=0,
        text_=text,
        embedding=fake.embed_one(text).tolist(),
        classification="public",
        department="procurement",
        effective_date=dt.date(2024, 1, 1),
        lineage_id=lineage,
    )
    db_session.add(chunk)
    await db_session.flush()
    return chunk


async def _login(client: AsyncClient, tenant_id, username, password) -> None:
    resp = await client.post(
        "/auth/login",
        json={"tenant_id": str(tenant_id), "username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_chat_ask_returns_full_payload(
    client, empire_tenant, seeded_executive, seeded_chunk
):
    _judge_cache_clear()
    await _login(client, empire_tenant.id, "ex-proc", "imperial-march")

    resp = await client.post("/chat/ask", json={"query": "anything", "top_k": 6})

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["query"] == "anything"
    assert payload["answer"]["text"].startswith("Answer about")
    assert payload["conflicts"] == []
    assert "citations" in payload


@pytest.mark.asyncio
async def test_chat_ask_unauthenticated_is_401(client):
    resp = await client.post("/chat/ask", json={"query": "q"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_ask_rejects_empty_query(client, empire_tenant, seeded_executive):
    _judge_cache_clear()
    await _login(client, empire_tenant.id, "ex-proc", "imperial-march")
    resp = await client.post("/chat/ask", json={"query": "   "})
    # Either pydantic min_length=1 (422) or explicit 400 from the router check
    assert resp.status_code in (400, 422)
