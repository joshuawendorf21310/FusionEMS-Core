"""Self-service onboarding, support chat, and platform events tables

Revision ID: 20260227_0013
Revises: 20260227_0012
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0013"
down_revision = "20260227_0012"
branch_labels = None
depends_on = None

_TABLES = [
    "legal_packets",
    "legal_documents",
    "legal_sign_events",
    "document_events",
    "onboarding_idempotency_keys",
    "submission_batches",
    "edi_artifacts",
    "claim_status_history",
    "claim_documents",
    "document_matches",
    "generated_pdfs",
    "support_threads",
    "support_messages",
    "support_escalations",
    "platform_events",
    "event_reads",
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"])
    op.create_index(f"ix_{name}_data", name, [sa.text("data")], postgresql_using="gin")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    for tbl in _TABLES:
        _standard_table(tbl)

    op.execute("CREATE INDEX ix_platform_events_cursor ON platform_events(tenant_id, created_at)")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_billing_cases_data_trgm "
        "ON billing_cases USING gin((data->>'patient_name') gin_trgm_ops)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_applications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            contact_email TEXT NOT NULL,
            agency_name TEXT NOT NULL,
            zip_code TEXT,
            agency_type TEXT,
            annual_call_volume INTEGER,
            current_billing_percent FLOAT,
            payer_mix JSONB DEFAULT '{}',
            level_mix JSONB DEFAULT '{}',
            selected_modules JSONB DEFAULT '[]',
            roi_snapshot_hash TEXT,
            status TEXT DEFAULT 'started',
            legal_status TEXT DEFAULT 'pending',
            tenant_id UUID,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            provisioned_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_onboarding_apps_email "
        "ON onboarding_applications(contact_email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_onboarding_apps_status ON onboarding_applications(status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_onboarding_apps_status")
    op.execute("DROP INDEX IF EXISTS ix_onboarding_apps_email")
    op.execute("DROP TABLE IF EXISTS onboarding_applications")
    op.execute("DROP INDEX IF EXISTS ix_billing_cases_data_trgm")

    for tbl in reversed(_TABLES):
        op.execute(f"DROP INDEX IF EXISTS ix_{tbl}_data")
        op.execute(f"DROP INDEX IF EXISTS ix_{tbl}_tenant_id")
        if tbl == "platform_events":
            op.execute("DROP INDEX IF EXISTS ix_platform_events_cursor")
        op.drop_table(tbl)
