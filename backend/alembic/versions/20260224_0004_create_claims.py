"""create claims table

Revision ID: 20260224_0004
Revises: 20260224_0003
Create Date: 2026-02-24 00:04:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0004"
down_revision: Union[str, None] = "20260224_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

claim_payer_type = sa.Enum("MEDICARE", "MEDICAID", "COMMERCIAL", "SELFPAY", "OTHER", name="claim_payer_type")
claim_service_level = sa.Enum("BLS", "ALS1", "ALS2", "SCT", "CCT", "OTHER", name="claim_service_level")
claim_status = sa.Enum(
    "draft", "pending_review", "ready_to_export", "exported", "submitted", "paid", "denied", "appeal_needed", "closed", name="claim_status"
)


def upgrade() -> None:
    claim_payer_type.create(op.get_bind(), checkfirst=True)
    claim_service_level.create(op.get_bind(), checkfirst=True)
    claim_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "claims",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payer_name", sa.String(length=255), nullable=False),
        sa.Column("payer_type", claim_payer_type, nullable=False),
        sa.Column("icd10_primary", sa.String(length=16), nullable=False),
        sa.Column("icd10_secondary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("modifiers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("service_level", claim_service_level, nullable=False),
        sa.Column("transport_flag", sa.Boolean(), nullable=False),
        sa.Column("origin_zip", sa.String(length=10), nullable=True),
        sa.Column("destination_zip", sa.String(length=10), nullable=True),
        sa.Column("mileage_loaded", sa.Float(), nullable=True),
        sa.Column("charge_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("patient_responsibility_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", claim_status, nullable=False),
        sa.Column("denial_reason_code", sa.String(length=32), nullable=True),
        sa.Column("denial_reason_text_redacted_flag", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claims_tenant_id"), "claims", ["tenant_id"], unique=False)
    op.create_index("ix_claims_tenant_status", "claims", ["tenant_id", "status"], unique=False)
    op.create_index("ix_claims_tenant_submitted_at", "claims", ["tenant_id", "submitted_at"], unique=False)
    op.create_index("ix_claims_tenant_incident", "claims", ["tenant_id", "incident_id"], unique=False)
    op.create_index("uq_claims_tenant_idempotency", "claims", ["tenant_id", "idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("uq_claims_tenant_idempotency", table_name="claims")
    op.drop_index("ix_claims_tenant_incident", table_name="claims")
    op.drop_index("ix_claims_tenant_submitted_at", table_name="claims")
    op.drop_index("ix_claims_tenant_status", table_name="claims")
    op.drop_index(op.f("ix_claims_tenant_id"), table_name="claims")
    op.drop_table("claims")
    claim_status.drop(op.get_bind(), checkfirst=True)
    claim_service_level.drop(op.get_bind(), checkfirst=True)
    claim_payer_type.drop(op.get_bind(), checkfirst=True)
