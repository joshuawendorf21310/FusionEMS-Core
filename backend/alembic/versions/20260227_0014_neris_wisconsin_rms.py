"""NERIS pack system, Wisconsin department config, and Fire RMS tables

Revision ID: 20260227_0014
Revises: 20260227_0013
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0014"
down_revision = "20260227_0013"
branch_labels = None
depends_on = None

_TABLES = [
    "neris_packs",
    "neris_pack_files",
    "neris_value_set_definitions",
    "neris_value_set_items",
    "neris_compiled_rules",
    "neris_onboarding",
    "fire_departments",
    "fire_stations",
    "fire_apparatus",
    "fire_personnel",
    "fire_incidents",
    "fire_incident_units",
    "fire_incident_actions",
    "fire_incident_outcomes",
    "fire_incident_documents",
]


def _standard_table(name: str) -> None:
    op.create_table(
        name,
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
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"])


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    for tbl in _TABLES:
        _standard_table(tbl)

    # ── NERIS Pack system: additional indexes ─────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_neris_packs_tenant ON neris_packs(tenant_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_packs_status "
        "ON neris_packs USING gin((data->>'status') gin_trgm_ops)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_pack_files_tenant ON neris_pack_files(tenant_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_vsd_tenant ON neris_value_set_definitions(tenant_id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_neris_vsi_tenant ON neris_value_set_items(tenant_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_vsi_def_id "
        "ON neris_value_set_items USING gin((data->>'definition_id') gin_trgm_ops)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_compiled_rules_tenant "
        "ON neris_compiled_rules(tenant_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_neris_onboarding_tenant ON neris_onboarding(tenant_id)"
    )

    # ── Wisconsin Department config: additional indexes ───────────────────────
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_departments_tenant ON fire_departments(tenant_id)"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_fire_stations_tenant ON fire_stations(tenant_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_fire_apparatus_tenant ON fire_apparatus(tenant_id)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_fire_personnel_tenant ON fire_personnel(tenant_id)")

    # ── Fire Incidents (RMS): additional indexes ──────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_fire_incidents_tenant ON fire_incidents(tenant_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incidents_dept "
        "ON fire_incidents USING gin((data->>'department_id') gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incidents_status ON fire_incidents((data->>'status'))"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incident_units_tenant ON fire_incident_units(tenant_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incident_actions_tenant "
        "ON fire_incident_actions(tenant_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incident_outcomes_tenant "
        "ON fire_incident_outcomes(tenant_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fire_incident_documents_tenant "
        "ON fire_incident_documents(tenant_id)"
    )


def downgrade() -> None:
    # Drop extra indexes then tables in reverse order
    op.execute("DROP INDEX IF EXISTS ix_fire_incident_documents_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_incident_outcomes_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_incident_actions_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_incident_units_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_incidents_status")
    op.execute("DROP INDEX IF EXISTS ix_fire_incidents_dept")
    op.execute("DROP INDEX IF EXISTS ix_fire_incidents_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_personnel_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_apparatus_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_stations_tenant")
    op.execute("DROP INDEX IF EXISTS ix_fire_departments_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_onboarding_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_compiled_rules_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_vsi_def_id")
    op.execute("DROP INDEX IF EXISTS ix_neris_vsi_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_vsd_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_pack_files_tenant")
    op.execute("DROP INDEX IF EXISTS ix_neris_packs_status")
    op.execute("DROP INDEX IF EXISTS ix_neris_packs_tenant")

    for tbl in reversed(_TABLES):
        op.execute(f"DROP INDEX IF EXISTS ix_{tbl}_tenant_id")
        op.drop_table(tbl)
