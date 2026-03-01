"""Add missing domination tables (Telnyx receipts, builders, templates)

Revision ID: 20260225_0005
Revises: 20260225_0004
Create Date: 2026-02-25

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260225_0005"
down_revision = "20260225_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind()

    op.create_table(
        "telnyx_webhook_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "builders_workflows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Enable RLS for new tenant tables
    for t in ["telnyx_webhook_receipts", "builders_workflows", "templates"]:
        op.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            f'CREATE POLICY "{t}_tenant_isolation" ON "{t}" USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid);'
        )


def downgrade() -> None:
    for t in ["templates", "builders_workflows", "telnyx_webhook_receipts"]:
        op.drop_table(t)
