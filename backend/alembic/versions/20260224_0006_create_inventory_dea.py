"""create inventory and narcotic logs

Revision ID: 20260224_0006
Revises: 20260224_0005
Create Date: 2026-02-24 03:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0006"
down_revision: Union[str, None] = "20260224_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    medication_schedule = sa.Enum("II", "III", "IV", "V", "UNSCHEDULED", name="medication_schedule")
    unit_of_measure = sa.Enum("MG", "ML", "UNIT", name="unit_of_measure")
    location_type = sa.Enum("station", "vehicle", "bag", name="location_type")
    narcotic_action = sa.Enum("STOCK_IN", "TRANSFER_OUT", "TRANSFER_IN", "ADMINISTERED", "WASTED", "ADJUSTMENT_WITH_REASON", name="narcotic_action")
    narcotic_uom = sa.Enum("MG", "ML", "UNIT", name="narcotic_uom")
    from_type = sa.Enum("station", "vehicle", "bag", name="narcotic_from_location_type")
    to_type = sa.Enum("station", "vehicle", "bag", name="narcotic_to_location_type")
    reason_code = sa.Enum("RECONCILIATION", "EXPIRATION", "DAMAGE", "WASTE", "OTHER", name="narcotic_reason_code")
    for e in [medication_schedule, unit_of_measure, location_type, narcotic_action, narcotic_uom, from_type, to_type, reason_code]:
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "medication_inventory",
        sa.Column("medication_name", sa.String(length=255), nullable=False),
        sa.Column("rxcui", sa.String(length=64), nullable=True),
        sa.Column("concentration", sa.String(length=128), nullable=True),
        sa.Column("form", sa.String(length=128), nullable=True),
        sa.Column("lot_number", sa.String(length=128), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column("schedule", medication_schedule, nullable=False),
        sa.Column("quantity_on_hand", sa.Float(), nullable=False),
        sa.Column("unit_of_measure", unit_of_measure, nullable=False),
        sa.Column("location_type", location_type, nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_medication_inventory_tenant_id"), "medication_inventory", ["tenant_id"], unique=False)
    op.create_index("ix_med_inventory_tenant_schedule", "medication_inventory", ["tenant_id", "schedule"], unique=False)
    op.create_index("ix_med_inventory_tenant_expiration", "medication_inventory", ["tenant_id", "expiration_date"], unique=False)
    op.create_index("ix_med_inventory_tenant_location", "medication_inventory", ["tenant_id", "location_type", "location_id"], unique=False)

    op.create_table(
        "narcotic_logs",
        sa.Column("inventory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", narcotic_action, nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_of_measure", narcotic_uom, nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_location_type", from_type, nullable=True),
        sa.Column("from_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_location_type", to_type, nullable=True),
        sa.Column("to_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("witness_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason_code", reason_code, nullable=False),
        sa.Column("note_redacted_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_id"], ["medication_inventory.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_narcotic_logs_tenant_id"), "narcotic_logs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_narcotic_logs_tenant_id"), table_name="narcotic_logs")
    op.drop_table("narcotic_logs")
    op.drop_index("ix_med_inventory_tenant_location", table_name="medication_inventory")
    op.drop_index("ix_med_inventory_tenant_expiration", table_name="medication_inventory")
    op.drop_index("ix_med_inventory_tenant_schedule", table_name="medication_inventory")
    op.drop_index(op.f("ix_medication_inventory_tenant_id"), table_name="medication_inventory")
    op.drop_table("medication_inventory")
