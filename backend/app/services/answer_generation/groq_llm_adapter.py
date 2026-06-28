"""Thin adapter exposing GroqLLMClient through the LlamaIndex `LLM` interface.

`CompactAndRefine.asynthesize()` (used by `generate_answer`) drives prompt
composition. The adapter forwards the resulting prompt to our existing
`GroqLLMClient.complete_text`, which owns the retry / fallback / rate-limit
ladder. Do not add behavior here beyond shape conversion.
"""
from __future__ import annotations

from typing import Any

from llama_index.core.base.llms.types import CompletionResponse, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.llms.custom import CustomLLM
from pydantic import ConfigDict, Field

# Inner client is duck-typed against `app.services.answer_generation.llm_client.LLMClient`
# (a typing.Protocol). Stored as `Any` because Pydantic v2 can't validate Protocol
# types in CustomLLM's pydantic-backed model. The runtime contract is exactly
# `complete_text(prompt: str) -> str`.


class HolocronGroqLLM(CustomLLM):
    """LlamaIndex `LLM` adapter that forwards every call to `inner_client.complete_text`.

    LlamaIndex's `CustomLLM` requires `complete()` (sync) and `stream_complete()`
    overrides; we additionally override `acomplete()` so the async synthesizer
    path is awaited end-to-end without spinning up a private event loop.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    inner_client: Any = Field(...)

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=8192,
            num_output=2048,
            model_name="holocron-groq",
            is_chat_model=False,
        )

    @llm_completion_callback()
    async def acomplete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        text = await self.inner_client.complete_text(prompt)
        return CompletionResponse(text=text)

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponse:
        # The async synthesizer path (`asynthesize`) is the supported entry point.
        # Surface misuse loudly rather than spinning up a hidden event loop.
        raise RuntimeError(
            "HolocronGroqLLM.complete() is sync-only; call .acomplete() from an "
            "async context, or use CompactAndRefine.asynthesize()."
        )

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError("HolocronGroqLLM does not support streaming")
