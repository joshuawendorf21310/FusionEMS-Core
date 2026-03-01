"""ops_control_platform: cases, cms_gate, hems, fleet_intelligence, ai_scheduling, maintenance_work_orders

Revision ID: 20260227_0015
Revises: 20260227_0014
Create Date: 2026-02-27
"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0015"
down_revision = "20260227_0014"
branch_labels = None
depends_on = None

_TABLES = [
    "cases",
    "cms_gate_results",
    "hems_acceptance_records",
    "hems_weather_briefs",
    "hems_risk_audits",
    "aircraft_readiness_events",
    "fleet_alerts",
    "maintenance_work_orders",
    "inspection_templates",
    "inspection_instances",
    "readiness_scores",
    "ai_scheduling_drafts",
]

_EXISTING = {"fleet_alerts"}


def upgrade() -> None:
    for table in _TABLES:
        if table in _EXISTING:
            continue
        op.create_table(
            table,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_index(f"ix_{table}_created_at", table, ["created_at"])

    op.execute("CREATE INDEX IF NOT EXISTS ix_cases_status ON cases USING gin((data->'status'));")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cases_transport_mode ON cases USING gin((data->'transport_mode'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_readiness_unit_id ON readiness_scores USING gin((data->'unit_id'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_maintenance_unit_id ON maintenance_work_orders USING gin((data->'unit_id'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hems_acceptance_mission ON hems_acceptance_records USING gin((data->'mission_id'));"
    )


def downgrade() -> None:
    for table in reversed(_TABLES):
        if table in _EXISTING:
            continue
        op.drop_table(table)
