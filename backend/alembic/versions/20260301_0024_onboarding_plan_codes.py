"""Add plan_code, tier_code, billing_tier_code, addon_codes to onboarding_applications

Revision ID: 20260301_0024
Revises: 20260227_0023
Create Date: 2026-03-01

Adds to onboarding_applications:
  - plan_code          VARCHAR(64)   nullable (SCHEDULING_ONLY, OPS_CORE, etc.)
  - tier_code          VARCHAR(64)   nullable (S1, S2, S3)
  - billing_tier_code  VARCHAR(64)   nullable (B1, B2, B3, B4)
  - addon_codes        JSONB         default '[]'
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260301_0024"
down_revision = "20260227_0023"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    table = "onboarding_applications"

    if not _col_exists(conn, table, "plan_code"):
        op.add_column(table, sa.Column("plan_code", sa.String(64), nullable=True))

    if not _col_exists(conn, table, "tier_code"):
        op.add_column(table, sa.Column("tier_code", sa.String(64), nullable=True))

    if not _col_exists(conn, table, "billing_tier_code"):
        op.add_column(table, sa.Column("billing_tier_code", sa.String(64), nullable=True))

    if not _col_exists(conn, table, "addon_codes"):
        op.add_column(
            table,
            sa.Column(
                "addon_codes",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default="'[]'::jsonb",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    table = "onboarding_applications"

    for col in ("addon_codes", "billing_tier_code", "tier_code", "plan_code"):
        if _col_exists(conn, table, col):
            op.drop_column(table, col)
