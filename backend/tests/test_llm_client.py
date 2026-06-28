from __future__ import annotations

import pytest

from app.services.answer_generation.llm_client import (
    FakeLLMClient,
    GroqLLMClient,
    LLMUnavailable,
)


@pytest.mark.asyncio
async def test_fake_returns_scripted_json():
    fake = FakeLLMClient(json_responses=[{"conflict": True, "subject": "x"}])
    out = await fake.complete_json("any prompt")
    assert out == {"conflict": True, "subject": "x"}
    assert fake.calls_json == ["any prompt"]


@pytest.mark.asyncio
async def test_fake_returns_scripted_text():
    fake = FakeLLMClient(text_responses=["hello [1] world"])
    out = await fake.complete_text("any prompt")
    assert out == "hello [1] world"
    assert fake.calls_text == ["any prompt"]


@pytest.mark.asyncio
async def test_fake_exhausting_responses_raises():
    fake = FakeLLMClient()
    with pytest.raises(IndexError):
        await fake.complete_json("p")


@pytest.mark.asyncio
async def test_groq_client_retries_then_falls_back(monkeypatch):
    """Wire a fake httpx-style 429 transport to assert the retry ladder."""

    attempts: list[str] = []

    class _FakeAPIError(Exception):
        def __init__(self, status: int):
            self.status = status

    async def fake_call(self, *, model: str, prompt: str, json_mode: bool):
        attempts.append(model)
        if model == self.primary:
            raise _FakeAPIError(429)
        # fallback succeeds on first attempt
        return "ok"

    monkeypatch.setattr(GroqLLMClient, "_raw_call", fake_call, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_is_rate_limit", lambda self, e: isinstance(e, _FakeAPIError) and e.status == 429, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_sleep", lambda self, _s: None, raising=False)

    c = GroqLLMClient(api_key="x", primary="prim", fallback="fb")
    out = await c.complete_text("p")
    assert out == "ok"
    # 3 attempts on primary, then 1 successful on fallback
    assert attempts == ["prim", "prim", "prim", "fb"]


@pytest.mark.asyncio
async def test_groq_raises_when_all_attempts_fail(monkeypatch):
    class _FakeAPIError(Exception):
        def __init__(self, status: int):
            self.status = status

    async def fake_call(self, *, model: str, prompt: str, json_mode: bool):
        raise _FakeAPIError(429)

    monkeypatch.setattr(GroqLLMClient, "_raw_call", fake_call, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_is_rate_limit", lambda self, e: True, raising=False)
    monkeypatch.setattr(GroqLLMClient, "_sleep", lambda self, _s: None, raising=False)

    c = GroqLLMClient(api_key="x", primary="prim", fallback="fb")
    with pytest.raises(LLMUnavailable):
        await c.complete_text("p")
