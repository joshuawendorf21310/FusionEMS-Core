"""create incidents table

Revision ID: 20260223_0001
Revises: 
Create Date: 2026-02-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260223_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


incident_status = sa.Enum("draft", "in_progress", "ready_for_review", "completed", "locked", name="incident_status")


def upgrade() -> None:
    incident_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "incidents",
        sa.Column("incident_number", sa.String(length=64), nullable=False),
        sa.Column("dispatch_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposition", sa.String(length=255), nullable=True),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "incident_number", name="uq_incidents_tenant_number"),
    )
    op.create_index(op.f("ix_incidents_incident_number"), "incidents", ["incident_number"], unique=False)
    op.create_index(op.f("ix_incidents_tenant_id"), "incidents", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_incidents_tenant_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_incident_number"), table_name="incidents")
    op.drop_table("incidents")
    incident_status.drop(op.get_bind(), checkfirst=True)
