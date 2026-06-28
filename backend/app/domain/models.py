from __future__ import annotations

import datetime as _dt
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Computed, Date, Integer, JSON, TIMESTAMP, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    role_label_map: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    max_clearance: Mapped[str] = mapped_column(String(32), nullable=False)
    departments: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    def __init__(self, **kw):  # ensure Python-side default for departments
        kw.setdefault("departments", [])
        super().__init__(**kw)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    lineage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    # Python attribute is `text_`; SQL column name is `text`. The trailing
    # underscore avoids shadowing the imported sqlalchemy `text` function
    # used elsewhere in this module for server_default expressions.
    text_: Mapped[str] = mapped_column("text", String, nullable=False)
    text_tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True), nullable=False
    )
    embedding: Mapped[Any] = mapped_column(Vector(768), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    lineage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entities: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )

    def __init__(self, **kw):
        kw.setdefault("entities", [])
        super().__init__(**kw)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    query_text: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieved_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    withheld_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    refusal_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    response_text: Mapped[str | None] = mapped_column(String, nullable=True)
    conflicts_found: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
