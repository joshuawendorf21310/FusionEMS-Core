"""Add LOB webhook receipts table

Revision ID: 20260225_0007
Revises: 20260225_0006
Create Date: 2026-02-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260225_0007"
down_revision = "20260225_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lob_webhook_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Enable RLS and tenant policy
    op.execute("ALTER TABLE lob_webhook_receipts ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY lob_webhook_receipts_tenant_isolation ON lob_webhook_receipts "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
    )


def downgrade() -> None:
    op.drop_table("lob_webhook_receipts")
