"""create vitals table

Revision ID: 20260224_0003
Revises: 20260224_0002
Create Date: 2026-02-24 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0003"
down_revision: str | None = "20260224_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vitals",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("spo2", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("gcs_total", sa.Integer(), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("etco2", sa.Float(), nullable=True),
        sa.Column("glucose_mgdl", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vitals_tenant_id"), "vitals", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_vitals_incident_id"), "vitals", ["incident_id"], unique=False)
    op.create_index(op.f("ix_vitals_patient_id"), "vitals", ["patient_id"], unique=False)
    op.create_index("ix_vitals_tenant_patient_taken_at", "vitals", ["tenant_id", "patient_id", "taken_at"], unique=False)
    op.create_index("ix_vitals_tenant_incident", "vitals", ["tenant_id", "incident_id"], unique=False)

    op.execute(
        """
        CREATE FUNCTION set_vitals_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_vitals_updated_at
        BEFORE UPDATE ON vitals
        FOR EACH ROW
        EXECUTE FUNCTION set_vitals_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_vitals_updated_at ON vitals;")
    op.execute("DROP FUNCTION IF EXISTS set_vitals_updated_at();")
    op.drop_index("ix_vitals_tenant_incident", table_name="vitals")
    op.drop_index("ix_vitals_tenant_patient_taken_at", table_name="vitals")
    op.drop_index(op.f("ix_vitals_patient_id"), table_name="vitals")
    op.drop_index(op.f("ix_vitals_incident_id"), table_name="vitals")
    op.drop_index(op.f("ix_vitals_tenant_id"), table_name="vitals")
    op.drop_table("vitals")
