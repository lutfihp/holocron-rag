from __future__ import annotations

import pytest

from app.core import warmup
from app.core.warmup import WarmState


@pytest.mark.asyncio
async def test_warm_sync_flips_both_flags(monkeypatch):
    state = WarmState()

    async def fake_bge():
        state.bge_ready = True

    async def fake_spacy():
        state.spacy_ready = True

    monkeypatch.setattr(warmup, "_warm_bge", fake_bge)
    monkeypatch.setattr(warmup, "_warm_spacy", fake_spacy)

    await warmup.warm_sync(state)

    assert state.bge_ready is True
    assert state.spacy_ready is True


@pytest.mark.asyncio
async def test_warm_groq_async_sets_flag(monkeypatch):
    state = WarmState()
    calls: list[str] = []

    async def fake_probe():
        calls.append("probed")

    monkeypatch.setattr(warmup, "_probe_groq", fake_probe)

    await warmup.warm_groq_async(state)

    assert calls == ["probed"]
    assert state.groq_ready is True


@pytest.mark.asyncio
async def test_probe_groq_swallows_failures(monkeypatch, caplog):
    """A Groq outage at startup must not propagate as an unhandled exception."""
    from app.services.answer_generation import llm_client

    class _Boom:
        async def complete_text(self, _prompt: str) -> str:
            raise RuntimeError("simulated outage")

    monkeypatch.setattr(llm_client, "get_default_llm", lambda: _Boom())
    await warmup._probe_groq()  # must not raise
