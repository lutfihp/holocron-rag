"""phase A initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")  # for gen_random_uuid()

    op.execute(
        """
        CREATE TABLE tenants (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            role_label_map  JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE TYPE clearance_level AS ENUM ('public','restricted','secret','top_secret');")

    op.execute(
        """
        CREATE TABLE users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            username        TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
            role            TEXT NOT NULL CHECK (role IN ('employee','manager','director','executive')),
            max_clearance   clearance_level NOT NULL,
            departments     TEXT[] NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, username)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE documents (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            title           TEXT NOT NULL,
            source_uri      TEXT,
            classification  clearance_level NOT NULL,
            department      TEXT NOT NULL,
            version         TEXT NOT NULL,
            effective_date  DATE NOT NULL,
            lineage_id      UUID NOT NULL,
            uploaded_by     UUID REFERENCES users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE chunks (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NOT NULL REFERENCES tenants(id),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            ordinal         INT NOT NULL,
            text            TEXT NOT NULL,
            text_tsv        TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
            embedding       VECTOR(768),
            classification  clearance_level NOT NULL,
            department      TEXT NOT NULL,
            effective_date  DATE NOT NULL,
            lineage_id      UUID NOT NULL,
            entities        TEXT[] NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        "CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);"
    )
    op.execute("CREATE INDEX chunks_text_tsv_gin ON chunks USING gin (text_tsv);")
    op.execute(
        "CREATE INDEX chunks_tenant_cls_dept ON chunks (tenant_id, classification, department);"
    )
    op.execute("CREATE INDEX chunks_lineage ON chunks (lineage_id);")

    op.execute(
        """
        CREATE TABLE audit_events (
            id              BIGSERIAL PRIMARY KEY,
            tenant_id       UUID NOT NULL,
            user_id         UUID NOT NULL,
            event_type      TEXT NOT NULL,
            query_text      TEXT,
            retrieved_ids   UUID[],
            withheld_ids    UUID[],
            refusal_ref     TEXT,
            response_text   TEXT,
            conflicts_found JSONB,
            latency_ms      INT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX audit_user_time ON audit_events (tenant_id, user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events;")
    op.execute("DROP TABLE IF EXISTS chunks;")
    op.execute("DROP TABLE IF EXISTS documents;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP TYPE  IF EXISTS clearance_level;")
    op.execute("DROP TABLE IF EXISTS tenants;")
