"""create idempotency receipts

Revision ID: 20260224_0005
Revises: 20260224_0004
Create Date: 2026-02-24 02:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0005"
down_revision: Union[str, None] = "20260224_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "idempotency_receipts",
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("route_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", "route_key", name="uq_idempotency_tenant_key_route"),
    )
    op.create_index(op.f("ix_idempotency_receipts_tenant_id"), "idempotency_receipts", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_receipts_tenant_id"), table_name="idempotency_receipts")
    op.drop_table("idempotency_receipts")
