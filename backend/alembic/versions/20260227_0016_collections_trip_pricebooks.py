"""collections_trip_pricebooks: AR ledger, soft collections, TRIP, pricebooks, entitlements

Revision ID: 20260227_0016
Revises: 20260227_0015
Create Date: 2026-02-27
"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0016"
down_revision = "20260227_0015"
branch_labels = None
depends_on = None

_NEW_TABLES = [
    "ar_accounts",
    "ar_charges",
    "ar_payments",
    "ar_payment_plans",
    "ar_disputes",
    "ar_statements",
    "collections_vendor_profiles",
    "collections_placements",
    "collections_status_updates",
    "collections_settings",
    "trip_settings",
    "trip_debts",
    "trip_exports",
    "trip_reject_imports",
    "trip_postings",
    "pricebooks",
    "pricebook_items",
    "ledger_entries",
    "usage_events",
    "tenant_billing_config",
    "billing_runs",
    "stripe_bootstrap_log",
    "entitlements",
]


def upgrade() -> None:
    for table in _NEW_TABLES:
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

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ar_accounts_status ON ar_accounts USING gin((data->'status'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ar_accounts_case_id ON ar_accounts USING gin((data->'case_id'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_trip_debts_status ON trip_debts USING gin((data->'status'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ledger_entries_type ON ledger_entries USING gin((data->'entry_type'));"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entitlements_plan ON entitlements USING gin((data->'plan_code'));"
    )


def downgrade() -> None:
    for table in reversed(_NEW_TABLES):
        op.drop_table(table)
