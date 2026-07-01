from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.healthz import router as healthz_router
from app.api.retrieval import router as retrieval_router
from app.api.user import router as user_router
from app.core.config import get_settings
from app.core.database import get_session
from app.core.logging import configure_logging
from app.core.warmup import WarmState, warm_groq_async, warm_sync

settings = get_settings()
configure_logging(pretty=settings.log_pretty)


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


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Bind one correlation_id for the request lifetime.

    Reads `x-correlation-id` from the inbound headers if present; otherwise
    generates a new UUID4. The same id is:
      - bound to structlog.contextvars (every log line gets it automatically)
      - written back as a response header (client / proxy can chain)
      - read by /chat/ask and used as audit_events.correlation_id
    """
    raw = request.headers.get("x-correlation-id")
    try:
        cid_uuid = uuid.UUID(raw) if raw else uuid.uuid4()
    except ValueError:
        # Inbound header isn't a UUID — generate fresh rather than persist a
        # client-supplied free-form string into audit_events.correlation_id.
        cid_uuid = uuid.uuid4()
    cid_str = str(cid_uuid)
    request.state.correlation_id = cid_uuid
    structlog.contextvars.bind_contextvars(correlation_id=cid_str)
    try:
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid_str
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


app.include_router(auth_router)
app.include_router(retrieval_router)
app.include_router(chat_router)
app.include_router(healthz_router)
app.include_router(admin_router)
app.include_router(user_router)
