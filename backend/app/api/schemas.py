from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    tenant_id: uuid.UUID
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TenantSummary(BaseModel):
    id: uuid.UUID
    name: str
    role_label: str  # the display label of THIS user's role in THIS tenant


class UserSummary(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    max_clearance: str
    departments: list[str]
    tenant: TenantSummary


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    score: float
    rank: int
    lineage_id: uuid.UUID


class RefusalSummary(BaseModel):
    withheld_count: int
    reference_id: str


class SearchResponseBody(BaseModel):
    results: list[SearchResultItem]
    refusal: RefusalSummary | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=10)


class AnswerOut(BaseModel):
    text: str
    cited_chunk_ids: list[uuid.UUID]


class CitationOut(BaseModel):
    marker: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    classification: str
    department: str
    effective_date: dt.date
    snippet: str
    lineage_id: uuid.UUID


class PositionOut(BaseModel):
    marker: int
    text: str


class ConflictOut(BaseModel):
    subject: str
    position_a: PositionOut
    position_b: PositionOut


class RefusalOut(BaseModel):
    reference_id: str
    withheld_count: int


class ChatResponse(BaseModel):
    query: str
    answer: AnswerOut
    citations: list[CitationOut]
    conflicts: list[ConflictOut]
    refusal: RefusalOut | None = None
