from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings


class LLMUnavailable(Exception):
    """Raised when all retry+fallback attempts have failed."""


class LLMClient(Protocol):
    async def complete_json(self, prompt: str) -> dict: ...
    async def complete_text(self, prompt: str) -> str: ...


@dataclass
class FakeLLMClient:
    """Scripted in-process LLM stand-in for tests.

    json_responses and text_responses are popped in order on each call.
    """

    json_responses: list[dict] = field(default_factory=list)
    text_responses: list[str] = field(default_factory=list)
    calls_json: list[str] = field(default_factory=list)
    calls_text: list[str] = field(default_factory=list)

    async def complete_json(self, prompt: str) -> dict:
        self.calls_json.append(prompt)
        return self.json_responses.pop(0)

    async def complete_text(self, prompt: str) -> str:
        self.calls_text.append(prompt)
        return self.text_responses.pop(0)


# Retry ladder per the spec §1.3 decision #8:
#   primary attempts 1..3 with backoff 0.5s, 1s, 2s
#   fallback attempts 1..3 with backoff 0.5s, 1s, 2s
_BACKOFFS = (0.5, 1.0, 2.0)


@dataclass
class GroqLLMClient:
    """Groq HTTP client with retry-and-fallback policy."""

    api_key: str
    primary: str
    fallback: str

    # ---- overridable seams for tests ----
    async def _raw_call(self, *, model: str, prompt: str, json_mode: bool) -> str:
        # Real implementation deferred to inline import so tests can monkeypatch.
        from groq import AsyncGroq  # type: ignore

        client = AsyncGroq(api_key=self.api_key)
        kwargs: dict[str, Any] = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def _is_rate_limit(self, exc: Exception) -> bool:
        # Groq SDK raises groq.APIStatusError with .status_code on 429
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        return status == 429

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    # ---- public API ----
    async def complete_json(self, prompt: str) -> dict:
        raw = await self._run_with_ladder(prompt, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMUnavailable(f"malformed JSON from LLM: {e}") from e

    async def complete_text(self, prompt: str) -> str:
        return await self._run_with_ladder(prompt, json_mode=False)

    async def _run_with_ladder(self, prompt: str, *, json_mode: bool) -> str:
        models = (self.primary, self.fallback)
        for m_idx, model in enumerate(models):
            for b_idx, backoff in enumerate(_BACKOFFS):
                try:
                    return await self._raw_call(model=model, prompt=prompt, json_mode=json_mode)
                except Exception as e:  # noqa: BLE001
                    if not self._is_rate_limit(e):
                        # Non-rate-limit: fail fast, do not try fallback model
                        raise LLMUnavailable(f"LLM call failed (non-429): {e}") from e
                    is_last = (m_idx == len(models) - 1) and (b_idx == len(_BACKOFFS) - 1)
                    if is_last:
                        continue
                    result = self._sleep(backoff)
                    if inspect.isawaitable(result):
                        await result
        raise LLMUnavailable("all primary and fallback attempts rate-limited")


@lru_cache
def get_default_llm() -> LLMClient:
    settings = get_settings()
    return GroqLLMClient(
        api_key=settings.groq_api_key,
        primary=settings.llm_primary_model,
        fallback=settings.llm_fallback_model,
    )
