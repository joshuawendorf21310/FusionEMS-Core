"""kitlink_ar: inventory, meds, kits, layouts, AR markers, ledger, narcotics, compliance

Revision ID: 20260227_0017
Revises: 20260227_0016
Create Date: 2026-02-27
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0017"
down_revision = "20260227_0016"
branch_labels = None
depends_on = None

_NEW_TABLES = [
    "inventory_items",
    "formulary_items",
    "kit_templates",
    "kit_compartments",
    "compartment_items",
    "unit_layouts",
    "unit_layout_kits",
    "ar_markers",
    "ar_marker_sheets",
    "inventory_transactions",
    "inventory_transaction_lines",
    "stock_locations",
    "stock_balances",
    "narc_kits",
    "narc_seals",
    "narc_counts",
    "narc_waste_events",
    "narc_discrepancies",
    "kitlink_ocr_jobs",
    "kitlink_anomaly_flags",
    "compliance_packs",
    "compliance_check_templates",
    "compliance_inspections",
    "compliance_findings",
    "kitlink_wizard_state",
]

_DOMINATION_DDL = """
CREATE TABLE IF NOT EXISTS {table} (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    version     INT NOT NULL DEFAULT 1,
    data        JSONB NOT NULL DEFAULT '{{}}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS {table}_tenant_idx ON {table}(tenant_id) WHERE deleted_at IS NULL;
"""


def upgrade() -> None:
    for table in _NEW_TABLES:
        op.execute(_DOMINATION_DDL.format(table=table))


def downgrade() -> None:
    for table in reversed(_NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
