"""hems_mission_events, rep_signatures, patient_statements view

Revision ID: 20260227_0020
Revises: 20260227_0019
Create Date: 2026-02-27
"""
from __future__ import annotations
from alembic import op

revision = "20260227_0020"
down_revision = "20260227_0019"
branch_labels = None
depends_on = None

DOMINATION_TABLES = [
    "hems_mission_events",
    "rep_signatures",
]


def upgrade() -> None:
    for name in DOMINATION_TABLES:
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {name} (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id   UUID NOT NULL,
                version     INTEGER NOT NULL DEFAULT 1,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                actor_user_id UUID,
                correlation_id TEXT,
                data        JSONB NOT NULL DEFAULT '{{}}'
            )
        """)
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_tenant ON {name}(tenant_id)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{name}_created ON {name}(created_at DESC)")

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_hems_mission_events_mission
        ON hems_mission_events USING gin((data->'mission_id'))
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_rep_signatures_rep
        ON rep_signatures USING gin((data->'rep_id'))
    """)


def downgrade() -> None:
    for name in reversed(DOMINATION_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {name}")
