"""create fire module tables

Revision ID: 20260224_0008
Revises: 20260224_0007
Create Date: 2026-02-24 04:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0008"
down_revision: Union[str, None] = "20260224_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    fire_incident_status = sa.Enum("draft", "in_progress", "completed", "locked", name="fire_incident_status")
    fire_inspection_status = sa.Enum("draft", "submitted", "approved", "closed", name="fire_inspection_status")
    fire_violation_severity = sa.Enum("low", "medium", "high", name="fire_violation_severity")
    for e in [fire_incident_status, fire_inspection_status, fire_violation_severity]:
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "fire_incidents",
        sa.Column("incident_number", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("address_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("incident_type", sa.String(length=64), nullable=False),
        sa.Column("status", fire_incident_status, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "incident_number", name="uq_fire_incidents_tenant_number"),
    )
    op.create_index(op.f("ix_fire_incidents_tenant_id"), "fire_incidents", ["tenant_id"], unique=False)

    op.create_table(
        "inspection_properties",
        sa.Column("address_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occupancy_type", sa.String(length=64), nullable=False),
        sa.Column("hazard_class", sa.String(length=64), nullable=False),
        sa.Column("owner_contact_redacted_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inspection_properties_tenant_id"), "inspection_properties", ["tenant_id"], unique=False)

    op.create_table(
        "fire_inspections",
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspector_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist_template_version_id", sa.String(length=64), nullable=False),
        sa.Column("findings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", fire_inspection_status, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fire_inspections_tenant_id"), "fire_inspections", ["tenant_id"], unique=False)

    op.create_table(
        "fire_inspection_violations",
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_reference", sa.String(length=128), nullable=False),
        sa.Column("severity", fire_violation_severity, nullable=False),
        sa.Column("correction_due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fire_inspection_violations_tenant_id"), "fire_inspection_violations", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fire_inspection_violations_tenant_id"), table_name="fire_inspection_violations")
    op.drop_table("fire_inspection_violations")
    op.drop_index(op.f("ix_fire_inspections_tenant_id"), table_name="fire_inspections")
    op.drop_table("fire_inspections")
    op.drop_index(op.f("ix_inspection_properties_tenant_id"), table_name="inspection_properties")
    op.drop_table("inspection_properties")
    op.drop_index(op.f("ix_fire_incidents_tenant_id"), table_name="fire_incidents")
    op.drop_table("fire_incidents")
