"""saas onboarding + roi + accreditation + fhir mapping tables

Revision ID: 0006
Revises: 20260225_0005_missing_tables
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260225_0006"
down_revision = "20260225_0005_missing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenant SaaS fields
    with op.batch_alter_table("tenants") as batch:
        batch.add_column(sa.Column("billing_tier", sa.String(length=64), server_default="starter", nullable=False))
        batch.add_column(sa.Column("modules_enabled", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
        batch.add_column(sa.Column("stripe_customer_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("stripe_subscription_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("billing_status", sa.String(length=32), server_default="inactive", nullable=False))
        batch.add_column(sa.Column("accreditation_status", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
        batch.add_column(sa.Column("compliance_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
        batch.add_column(sa.Column("feature_flags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))

    # Self-service onboarding
    op.create_table(
        "onboarding_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("agency_name", sa.String(length=255), nullable=False),
        sa.Column("zip_code", sa.String(length=16), nullable=False),
        sa.Column("agency_type", sa.String(length=32), nullable=False),
        sa.Column("annual_call_volume", sa.Integer(), nullable=False),
        sa.Column("current_billing_percent", sa.Numeric(5,2), nullable=False),
        sa.Column("payer_mix", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("level_mix", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("selected_modules", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("roi_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="started", nullable=False),
    )
    op.create_index("ix_onboarding_applications_email", "onboarding_applications", ["email"])

    # ROI scenarios (exportable + reproducible)
    op.create_table(
        "roi_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("zip_code", sa.String(length=16), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outputs_hash", sa.String(length=64), nullable=False),
    )

    # Accreditation engine
    op.create_table(
        "accreditation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("standard_ref", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("required_docs", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="not_started", nullable=False),
        sa.Column("score_weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_accreditation_items_tenant", "accreditation_items", ["tenant_id", "category"])

    op.create_table(
        "accreditation_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_accreditation_evidence_item", "accreditation_evidence", ["tenant_id", "item_id"])

    # FHIR mapping log (R4 JSON)
    op.create_table(
        "fhir_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )

    # Enable RLS policies for new tenant tables
    for tbl in ["accreditation_items", "accreditation_evidence", "fhir_artifacts"]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""CREATE POLICY {tbl}_tenant_isolation ON {tbl}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)"""
        )


def downgrade() -> None:
    for tbl in ["fhir_artifacts", "accreditation_evidence", "accreditation_items", "roi_scenarios", "onboarding_applications"]:
        op.drop_table(tbl)
    with op.batch_alter_table("tenants") as batch:
        batch.drop_column("feature_flags")
        batch.drop_column("compliance_metadata")
        batch.drop_column("accreditation_status")
        batch.drop_column("billing_status")
        batch.drop_column("stripe_subscription_id")
        batch.drop_column("stripe_customer_id")
        batch.drop_column("modules_enabled")
        batch.drop_column("billing_tier")
