"""payments and builders_rulesets domination tables

Revision ID: 20260227_0019
Revises: 20260227_0018
Create Date: 2026-02-27
"""
from __future__ import annotations
from alembic import op

revision = "20260227_0019"
down_revision = "20260227_0018"
branch_labels = None
depends_on = None

_NEW_TABLES = [
    "payments",
    "builders_rulesets",
]

_DOMINATION_DDL = """
CREATE TABLE IF NOT EXISTS {table} (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    version     INT NOT NULL DEFAULT 1,
    data        JSONB NOT NULL DEFAULT '{{}}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS {table}_tenant_idx ON {table}(tenant_id) WHERE deleted_at IS NULL;
"""


def upgrade() -> None:
    for table in _NEW_TABLES:
        op.execute(_DOMINATION_DDL.format(table=table))


def downgrade() -> None:
    for table in reversed(_NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
