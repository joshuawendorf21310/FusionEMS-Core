"""create integration registry

Revision ID: 20260224_0004
Revises: 20260224_0003
Create Date: 2026-02-24 01:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0004"
down_revision: Union[str, None] = "20260224_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    integration_provider = sa.Enum(
        "STRIPE", "TELNYX", "WEATHER", "REDIS", "SES", "OPENAI", "OTHER", name="integration_provider"
    )
    integration_provider.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "integration_registry",
        sa.Column("provider_name", integration_provider, nullable=False),
        sa.Column("enabled_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("config_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("config_encrypted_data_key", sa.LargeBinary(), nullable=False),
        sa.Column("config_key_id", sa.String(length=256), nullable=False),
        sa.Column("config_nonce", sa.String(length=128), nullable=False),
        sa.Column("config_kms_encryption_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider_name", name="uq_integration_registry_tenant_provider"),
    )
    op.create_index(op.f("ix_integration_registry_tenant_id"), "integration_registry", ["tenant_id"], unique=False)
    op.create_index(
        "ix_integration_registry_tenant_provider",
        "integration_registry",
        ["tenant_id", "provider_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_integration_registry_tenant_provider", table_name="integration_registry")
    op.drop_index(op.f("ix_integration_registry_tenant_id"), table_name="integration_registry")
    op.drop_table("integration_registry")
    sa.Enum(name="integration_provider").drop(op.get_bind(), checkfirst=True)
