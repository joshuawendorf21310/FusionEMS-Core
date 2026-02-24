"""add claim idempotency key

Revision ID: 20260224_0005
Revises: 20260224_0004
Create Date: 2026-02-24 00:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260224_0005"
down_revision: Union[str, None] = "20260224_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_index(
        "uq_claims_tenant_idempotency_key",
        "claims",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_claims_tenant_idempotency_key", table_name="claims")
    op.drop_column("claims", "idempotency_key")
