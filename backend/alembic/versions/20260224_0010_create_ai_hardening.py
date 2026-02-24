"""create ai hardening tables

Revision ID: 20260224_0010
Revises: 20260224_0009
Create Date: 2026-02-24 06:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0010"
down_revision: Union[str, None] = "20260224_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ai_run_type = sa.Enum(
        "BILLING_ANALYSIS",
        "ICD10_SUGGESTION",
        "MODIFIER_SUGGESTION",
        "DENIAL_RISK",
        "APPEAL_DRAFT",
        "TRANSCRIPT_SUMMARY",
        name="ai_run_type",
    )
    ai_run_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_runs",
        sa.Column("run_type", ai_run_type, nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("provenance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_runs_tenant_id"), "ai_runs", ["tenant_id"], unique=False)

    op.create_table(
        "ai_policies",
        sa.Column("allow_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requires_human_confirmation", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_policies_tenant_id"), "ai_policies", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_policies_tenant_id"), table_name="ai_policies")
    op.drop_table("ai_policies")
    op.drop_index(op.f("ix_ai_runs_tenant_id"), table_name="ai_runs")
    op.drop_table("ai_runs")
