from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    score: float
    rank: int


@dataclass(frozen=True)
class RefusalContext:
    reference_id: str
    withheld_count: int
    withheld_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[RetrievalResult, ...] = field(default_factory=tuple)
    refusal: RefusalContext | None = None
