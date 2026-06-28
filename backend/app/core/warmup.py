"""Startup warming: load BGE + spaCy synchronously, probe Groq asynchronously.

Lifespan flow in `app.main`:
    state = WarmState()
    app.state.warm = state
    if not settings.skip_warmup:
        await warm_sync(state)                  # blocks until BGE + spaCy ready
        asyncio.create_task(warm_groq_async(state))  # fire-and-forget probe

Each warm function flips one flag on the shared WarmState. /healthz/ready reads
the flags via app.state.warm.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class WarmState:
    bge_ready: bool = False
    spacy_ready: bool = False
    groq_ready: bool = False


async def _warm_bge() -> None:
    """Load the BGE provider and run one embed pass to materialize the tensor graph."""
    from app.services.ingestion.embedding_factory import get_default_embedder
    embedder = get_default_embedder()
    # BGE encode is CPU-bound; run in a thread so the event loop stays free.
    await asyncio.to_thread(embedder.embed_one, "warmup")


async def _warm_spacy() -> None:
    """Load the default spaCy pipeline + parse one doc to materialize it."""
    from app.services.ingestion.entity_extractor import get_default_extractor
    nlp = get_default_extractor()
    await asyncio.to_thread(nlp, "Warmup of the spaCy pipeline.")


async def _probe_groq() -> None:
    """Best-effort one-call probe so the first /chat/ask doesn't pay TLS setup.

    Swallows failures: a Groq outage at startup must not crash the app.
    """
    try:
        from app.services.answer_generation.llm_client import get_default_llm
        llm = get_default_llm()
        await llm.complete_text("ping")
    except Exception as e:  # noqa: BLE001
        logger.warning("groq warmup probe failed: %s", e)


async def warm_sync(state: WarmState) -> None:
    await _warm_bge()
    state.bge_ready = True
    await _warm_spacy()
    state.spacy_ready = True


async def warm_groq_async(state: WarmState) -> None:
    await _probe_groq()
    state.groq_ready = True
