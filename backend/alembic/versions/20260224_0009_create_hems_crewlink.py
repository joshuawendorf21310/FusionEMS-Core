"""create hems crewlink tables

Revision ID: 20260224_0009
Revises: 20260224_0008
Create Date: 2026-02-24 05:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260224_0009"
down_revision: Union[str, None] = "20260224_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    flight_status = sa.Enum("REQUESTED", "ACCEPTED", "ENROUTE", "COMPLETE", "CANCELLED", name="flight_request_status")
    flight_priority = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="flight_priority")
    paging_channel = sa.Enum("push", "sms", "email", name="paging_channel")
    for e in [flight_status, flight_priority, paging_channel]:
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "flight_requests",
        sa.Column("request_number", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requesting_facility_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("patient_summary_redacted_flag", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", flight_priority, nullable=False),
        sa.Column("status", flight_status, nullable=False),
        sa.Column("accepted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "request_number", name="uq_flight_requests_tenant_request_number"),
    )
    op.create_index(op.f("ix_flight_requests_tenant_id"), "flight_requests", ["tenant_id"], unique=False)

    op.create_table(
        "crew_availability",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qualification_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crew_availability_tenant_id"), "crew_availability", ["tenant_id"], unique=False)

    op.create_table(
        "paging_events",
        sa.Column("flight_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", paging_channel, nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_paging_events_tenant_id"), "paging_events", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_paging_events_tenant_id"), table_name="paging_events")
    op.drop_table("paging_events")
    op.drop_index(op.f("ix_crew_availability_tenant_id"), table_name="crew_availability")
    op.drop_table("crew_availability")
    op.drop_index(op.f("ix_flight_requests_tenant_id"), table_name="flight_requests")
    op.drop_table("flight_requests")
