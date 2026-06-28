"""phase D: add correlation_id to audit_events

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No backfill: Phase C demo audit rows (if any) are wiped before this migration.
    # If any rows exist they would fail NOT NULL; that is intentional — the project
    # has no production data and re-seeding via the demo path is trivial.
    op.execute("TRUNCATE TABLE audit_events")
    op.execute(
        """
        ALTER TABLE audit_events
        ADD COLUMN correlation_id UUID NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX audit_correlation
        ON audit_events (tenant_id, correlation_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS audit_correlation")
    op.execute("ALTER TABLE audit_events DROP COLUMN IF EXISTS correlation_id")
