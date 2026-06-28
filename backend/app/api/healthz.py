from __future__ import annotations

from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/healthz", tags=["healthz"])


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict:
    """Readiness probe. 200 once BGE + spaCy are warmed; 503 otherwise.

    Groq readiness is reported in `checks.groq` but does NOT gate the 200,
    because (a) Groq is best-effort and (b) we don't want a temporary Groq
    outage to mark the whole app unready for /healthz/ready consumers."""
    state = getattr(request.app.state, "warm", None)
    bge = bool(state and state.bge_ready)
    spacy = bool(state and state.spacy_ready)
    groq = bool(state and state.groq_ready)
    is_ready = bge and spacy
    if not is_ready:
        response.status_code = 503
    return {
        "ready": is_ready,
        "checks": {"bge": bge, "spacy": spacy, "groq": groq},
    }
