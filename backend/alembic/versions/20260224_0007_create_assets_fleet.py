"""create assets and fleet tables

Revision ID: 20260224_0007
Revises: 20260224_0006
Create Date: 2026-02-24 04:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0007"
down_revision: Union[str, None] = "20260224_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    asset_status = sa.Enum("IN_SERVICE", "OUT_OF_SERVICE", "MAINTENANCE", name="asset_status")
    vehicle_status = sa.Enum("IN_SERVICE", "OUT_OF_SERVICE", "MAINTENANCE", name="vehicle_status")
    vehicle_type = sa.Enum("ALS_AMBULANCE", "BLS_AMBULANCE", "ENGINE", "LADDER", "SUPERVISOR", "AIRCRAFT", "OTHER", name="vehicle_type")
    maintenance_event_type = sa.Enum("OIL_CHANGE", "TIRE", "BRAKES", "INSPECTION", "REPAIR", "OTHER", name="maintenance_event_type")
    for e in [asset_status, vehicle_status, vehicle_type, maintenance_event_type]:
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assets",
        sa.Column("asset_tag", sa.String(length=128), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("status", asset_status, nullable=False),
        sa.Column("assigned_location_type", sa.String(length=64), nullable=True),
        sa.Column("assigned_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_inspection_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "asset_tag", name="uq_assets_tenant_asset_tag"),
    )
    op.create_index(op.f("ix_assets_tenant_id"), "assets", ["tenant_id"], unique=False)

    op.create_table(
        "vehicles",
        sa.Column("unit_identifier", sa.String(length=128), nullable=False),
        sa.Column("vin", sa.String(length=64), nullable=True),
        sa.Column("vehicle_type", vehicle_type, nullable=False),
        sa.Column("status", vehicle_status, nullable=False),
        sa.Column("current_mileage", sa.Integer(), nullable=False),
        sa.Column("current_engine_hours", sa.Float(), nullable=False),
        sa.Column("last_service_at_mileage", sa.Integer(), nullable=True),
        sa.Column("next_service_due_mileage", sa.Integer(), nullable=True),
        sa.Column("last_service_at_date", sa.Date(), nullable=True),
        sa.Column("next_service_due_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "unit_identifier", name="uq_vehicles_tenant_unit_identifier"),
    )
    op.create_index(op.f("ix_vehicles_tenant_id"), "vehicles", ["tenant_id"], unique=False)

    op.create_table(
        "maintenance_events",
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", maintenance_event_type, nullable=False),
        sa.Column("due_mileage", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_mileage", sa.Integer(), nullable=True),
        sa.Column("cost_amount", sa.Float(), nullable=True),
        sa.Column("vendor_name", sa.String(length=255), nullable=True),
        sa.Column("notes_redacted_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_maintenance_events_tenant_id"), "maintenance_events", ["tenant_id"], unique=False)
    op.create_index("ix_maintenance_events_tenant_vehicle", "maintenance_events", ["tenant_id", "vehicle_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_maintenance_events_tenant_vehicle", table_name="maintenance_events")
    op.drop_index(op.f("ix_maintenance_events_tenant_id"), table_name="maintenance_events")
    op.drop_table("maintenance_events")
    op.drop_index(op.f("ix_vehicles_tenant_id"), table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index(op.f("ix_assets_tenant_id"), table_name="assets")
    op.drop_table("assets")
