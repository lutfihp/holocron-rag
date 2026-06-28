from __future__ import annotations

import pytest

from app.services.answer_generation.groq_llm_adapter import HolocronGroqLLM
from app.services.answer_generation.llm_client import FakeLLMClient


@pytest.mark.asyncio
async def test_adapter_acomplete_forwards_to_inner_client():
    inner = FakeLLMClient(text_responses=["adapter response"])
    adapter = HolocronGroqLLM(inner_client=inner)

    response = await adapter.acomplete("hello")

    assert response.text == "adapter response"
    assert inner.calls_text == ["hello"]


def test_adapter_metadata_model_name():
    """LlamaIndex registers LLMs by metadata.model_name; lock the name."""
    inner = FakeLLMClient()
    adapter = HolocronGroqLLM(inner_client=inner)
    assert adapter.metadata.model_name == "holocron-groq"


def test_adapter_metadata_marks_non_streaming():
    inner = FakeLLMClient()
    adapter = HolocronGroqLLM(inner_client=inner)
    assert adapter.metadata.is_chat_model is False
