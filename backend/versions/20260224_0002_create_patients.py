"""create patients table

Revision ID: 20260224_0002
Revises: 20260223_0001
Create Date: 2026-02-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260224_0002"
down_revision: str | None = "20260223_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


patient_gender = sa.Enum("female", "male", "non_binary", "other", "unknown", name="patient_gender")


def upgrade() -> None:
    patient_gender.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "patients",
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("middle_name", sa.String(length=120), nullable=True),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("gender", patient_gender, nullable=False),
        sa.Column("external_identifier", sa.String(length=64), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "date_of_birth IS NOT NULL OR age_years IS NOT NULL", name="ck_patients_dob_or_age"
        ),
    )
    op.create_index(op.f("ix_patients_tenant_id"), "patients", ["tenant_id"], unique=False)
    op.create_index(
        "ix_patients_tenant_incident", "patients", ["tenant_id", "incident_id"], unique=False
    )
    op.create_index("ix_patients_tenant_gender", "patients", ["tenant_id", "gender"], unique=False)

    op.execute(
        """
        CREATE FUNCTION set_patients_updated_at()
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
        CREATE TRIGGER trg_patients_updated_at
        BEFORE UPDATE ON patients
        FOR EACH ROW
        EXECUTE FUNCTION set_patients_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_patients_updated_at ON patients;")
    op.execute("DROP FUNCTION IF EXISTS set_patients_updated_at();")
    op.drop_index("ix_patients_tenant_gender", table_name="patients")
    op.drop_index("ix_patients_tenant_incident", table_name="patients")
    op.drop_index(op.f("ix_patients_tenant_id"), table_name="patients")
    op.drop_table("patients")
    patient_gender.drop(op.get_bind(), checkfirst=True)
