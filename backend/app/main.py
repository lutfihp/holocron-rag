from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.healthz import router as healthz_router
from app.api.retrieval import router as retrieval_router
from app.core.config import get_settings
from app.core.database import get_session
from app.core.warmup import WarmState, warm_groq_async, warm_sync

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = WarmState()
    app.state.warm = state
    if not settings.skip_warmup:
        await warm_sync(state)
        # Fire-and-forget Groq probe; failure logged but does not block startup.
        asyncio.create_task(warm_groq_async(state))
    else:
        # Dev / test mode: declare core ready immediately. First request after
        # reload pays full BGE + spaCy load cost; demos must run without this.
        state.bge_ready = True
        state.spacy_ready = True
    yield


app = FastAPI(title="HOLOCRON", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(auth_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(healthz_router)
