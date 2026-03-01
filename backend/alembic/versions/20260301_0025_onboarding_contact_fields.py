"""Add contact fields to onboarding_applications

Revision ID: 20260301_0025
Revises: 20260301_0024
Create Date: 2026-03-01

Adds to onboarding_applications:
  - first_name              VARCHAR(120)  nullable
  - last_name               VARCHAR(120)  nullable
  - phone                   VARCHAR(40)   nullable
  - is_government_entity    BOOLEAN       default false
  - collections_mode        VARCHAR(32)   default 'none'
  - statement_channels      JSONB         default '["mail"]'
  - collector_vendor_name   VARCHAR(200)  nullable
  - placement_method        VARCHAR(64)   default 'portal_upload'
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260301_0025"
down_revision = "20260301_0024"
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

    if not _col_exists(conn, table, "first_name"):
        op.add_column(table, sa.Column("first_name", sa.String(120), nullable=True))

    if not _col_exists(conn, table, "last_name"):
        op.add_column(table, sa.Column("last_name", sa.String(120), nullable=True))

    if not _col_exists(conn, table, "phone"):
        op.add_column(table, sa.Column("phone", sa.String(40), nullable=True))

    if not _col_exists(conn, table, "is_government_entity"):
        op.add_column(
            table,
            sa.Column("is_government_entity", sa.Boolean(), nullable=False, server_default="false"),
        )

    if not _col_exists(conn, table, "collections_mode"):
        op.add_column(
            table,
            sa.Column("collections_mode", sa.String(32), nullable=False, server_default="none"),
        )

    if not _col_exists(conn, table, "statement_channels"):
        op.add_column(
            table,
            sa.Column(
                "statement_channels",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default='\'["mail"]\'::jsonb',
            ),
        )

    if not _col_exists(conn, table, "collector_vendor_name"):
        op.add_column(table, sa.Column("collector_vendor_name", sa.String(200), nullable=True))

    if not _col_exists(conn, table, "placement_method"):
        op.add_column(
            table,
            sa.Column("placement_method", sa.String(64), nullable=False, server_default="portal_upload"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    table = "onboarding_applications"

    for col in (
        "placement_method",
        "collector_vendor_name",
        "statement_channels",
        "collections_mode",
        "is_government_entity",
        "phone",
        "last_name",
        "first_name",
    ):
        if _col_exists(conn, table, col):
            op.drop_column(table, col)
