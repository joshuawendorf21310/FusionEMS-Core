"""Telnyx Voice/SMS/Fax tables: tenant_phone_numbers, telnyx_events, telnyx_calls,
telnyx_sms_messages, telnyx_opt_outs, fax_documents

Revision ID: 20260226_0010
Revises: 20260226_0009
Create Date: 2026-02-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260226_0010"
down_revision = "20260226_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # tenant_phone_numbers
    # Maps a Telnyx DID (E.164) to a tenant and purpose.
    # ------------------------------------------------------------------
    op.create_table(
        "tenant_phone_numbers",
        sa.Column("phone_e164", sa.String(length=20), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "purpose",
            sa.String(length=32),
            nullable=False,
            comment="billing_voice | billing_sms | billing_fax",
        ),
        sa.Column("forward_to_phone_e164", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tenant_phone_numbers_tenant", "tenant_phone_numbers", ["tenant_id", "purpose"])

    # ------------------------------------------------------------------
    # telnyx_events
    # Idempotency store for every inbound Telnyx webhook event.
    # ------------------------------------------------------------------
    op.create_table(
        "telnyx_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_telnyx_events_type_received", "telnyx_events", ["event_type", "received_at"])

    # ------------------------------------------------------------------
    # telnyx_calls
    # Per-call IVR state machine record.
    # ------------------------------------------------------------------
    op.create_table(
        "telnyx_calls",
        sa.Column("call_control_id", sa.String(length=256), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("from_phone", sa.String(length=20), nullable=False),
        sa.Column("to_phone", sa.String(length=20), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="MENU"),
        sa.Column("statement_id", sa.String(length=64), nullable=True),
        sa.Column("sms_phone", sa.String(length=20), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_telnyx_calls_tenant_state", "telnyx_calls", ["tenant_id", "state"])

    # ------------------------------------------------------------------
    # telnyx_sms_messages
    # Audit log for every inbound and outbound SMS.
    # ------------------------------------------------------------------
    op.create_table(
        "telnyx_sms_messages",
        sa.Column("message_id", sa.String(length=256), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("direction", sa.String(length=3), nullable=False, comment="IN | OUT"),
        sa.Column("from_phone", sa.String(length=20), nullable=False),
        sa.Column("to_phone", sa.String(length=20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_telnyx_sms_tenant_direction", "telnyx_sms_messages", ["tenant_id", "direction", "created_at"])

    # ------------------------------------------------------------------
    # telnyx_opt_outs
    # TCPA-compliant SMS opt-out registry per tenant+phone.
    # ------------------------------------------------------------------
    op.create_table(
        "telnyx_opt_outs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="sms_stop"),
        sa.PrimaryKeyConstraint("tenant_id", "phone_e164"),
    )
    op.create_index("ix_telnyx_opt_outs_phone", "telnyx_opt_outs", ["phone_e164"])

    # ------------------------------------------------------------------
    # fax_documents
    # Tracks every inbound fax document stored to S3.
    # ------------------------------------------------------------------
    op.create_table(
        "fax_documents",
        sa.Column("fax_id", sa.String(length=256), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("from_phone", sa.String(length=20), nullable=False),
        sa.Column("to_phone", sa.String(length=20), nullable=False),
        sa.Column("s3_key_original", sa.Text(), nullable=True),
        sa.Column("sha256_original", sa.String(length=64), nullable=True),
        sa.Column("doc_type", sa.String(length=64), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_fetch"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fax_documents_tenant_status", "fax_documents", ["tenant_id", "status"])

    # ------------------------------------------------------------------
    # Enable RLS on tenant-scoped tables
    # tenant_phone_numbers is system-managed (no per-tenant isolation needed)
    # telnyx_events and telnyx_calls may receive events before tenant is resolved
    # so we only apply RLS to the tables with guaranteed tenant_id columns.
    # ------------------------------------------------------------------
    for tbl in ("telnyx_sms_messages", "telnyx_opt_outs", "fax_documents"):
        op.execute(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            f'CREATE POLICY "{tbl}_tenant_isolation" ON "{tbl}" '
            f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
        )


def downgrade() -> None:
    for tbl in ("telnyx_sms_messages", "telnyx_opt_outs", "fax_documents"):
        op.execute(f'DROP POLICY IF EXISTS "{tbl}_tenant_isolation" ON "{tbl}";')
        op.execute(f'ALTER TABLE "{tbl}" DISABLE ROW LEVEL SECURITY;')

    for tbl in (
        "fax_documents",
        "telnyx_opt_outs",
        "telnyx_sms_messages",
        "telnyx_calls",
        "telnyx_events",
        "tenant_phone_numbers",
    ):
        op.drop_table(tbl)
