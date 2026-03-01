"""Founder Copilot chat tables + Voice advanced tables

Revision ID: 20260227_0021
Revises: 20260227_0020
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20260227_0021"
down_revision = "20260227_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Founder Copilot ───────────────────────────────────────────────────────
    op.create_table(
        "founder_chat_sessions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("founder_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New session"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_founder_chat_sessions_user", "founder_chat_sessions", ["founder_user_id"])

    op.create_table(
        "founder_chat_messages",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("founder_chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_founder_chat_messages_session", "founder_chat_messages", ["session_id"])

    op.create_table(
        "founder_chat_runs",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("founder_chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="proposed"),
        sa.Column("plan_json", JSONB, nullable=True),
        sa.Column("gh_run_id", sa.String(128), nullable=True),
        sa.Column("gh_run_url", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_founder_chat_runs_session", "founder_chat_runs", ["session_id"])

    op.create_table(
        "founder_chat_actions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("founder_chat_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("payload_json", JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="proposed"),
        sa.Column("result_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_founder_chat_actions_run", "founder_chat_actions", ["run_id"])

    # ── Voice advanced tables ─────────────────────────────────────────────────
    op.create_table(
        "voice_screen_pops",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("call_control_id", sa.String(128), nullable=True),
        sa.Column("caller_phone", sa.String(32), nullable=True),
        sa.Column("data_json", JSONB, nullable=True),
        sa.Column(
            "popped_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dismissed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_voice_screen_pops_tenant", "voice_screen_pops", ["tenant_id"])

    op.create_table(
        "voice_alert_policies",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("condition_json", JSONB, nullable=True),
        sa.Column("action_json", JSONB, nullable=True),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_voice_alert_policies_tenant", "voice_alert_policies", ["tenant_id"])

    op.create_table(
        "voice_script_packs",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scripts_json", JSONB, nullable=True),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_voice_script_packs_tenant", "voice_script_packs", ["tenant_id"])

    op.create_table(
        "voice_compliance_guard_events",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("call_control_id", sa.String(128), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("details_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_voice_compliance_guard_call", "voice_compliance_guard_events", ["call_control_id"]
    )

    op.create_table(
        "voice_onboarding_sessions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("caller_phone", sa.String(32), nullable=True),
        sa.Column("step", sa.String(64), nullable=True),
        sa.Column("data_json", JSONB, nullable=True),
        sa.Column("completed", sa.Boolean, server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_voice_onboarding_tenant", "voice_onboarding_sessions", ["tenant_id"])

    op.create_table(
        "voice_founder_busy_states",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "voice_callback_slots",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("caller_phone", sa.String(32), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_voice_callback_slots_status", "voice_callback_slots", ["status", "scheduled_at"]
    )

    op.create_table(
        "voice_ab_tests",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("variants_json", JSONB, nullable=True),
        sa.Column("status", sa.String(32), server_default="running", nullable=False),
        sa.Column("results_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "voice_cost_caps",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("cap_cents", sa.Integer, nullable=False),
        sa.Column("period", sa.String(32), server_default="monthly", nullable=False),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "voice_preferences",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("caller_phone", sa.String(32), nullable=False),
        sa.Column("preference_key", sa.String(128), nullable=False),
        sa.Column("preference_value", sa.Text, nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_voice_preferences_tenant_phone", "voice_preferences", ["tenant_id", "caller_phone"]
    )

    op.create_table(
        "voice_recording_governance",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("retention_days", sa.Integer, server_default="90", nullable=False),
        sa.Column("consent_required", sa.Boolean, server_default="true", nullable=False),
        sa.Column("active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("policy_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_voice_recording_governance_tenant", "voice_recording_governance", ["tenant_id"]
    )

    op.create_table(
        "voice_recording_access_log",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("recording_id", sa.String(128), nullable=True),
        sa.Column("accessed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("access_reason", sa.String(255), nullable=True),
        sa.Column(
            "accessed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_voice_recording_access_log_tenant",
        "voice_recording_access_log",
        ["tenant_id", "accessed_at"],
    )

    op.create_table(
        "voice_war_room_incidents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("severity", sa.String(32), nullable=True),
        sa.Column(
            "activated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_voice_war_room_status", "voice_war_room_incidents", ["status"])

    op.create_table(
        "voice_human_review_queue",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("call_control_id", sa.String(128), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("assigned_to", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_voice_human_review_status", "voice_human_review_queue", ["status", "created_at"]
    )

    op.create_table(
        "voice_improvement_tickets",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), server_default="open", nullable=False),
        sa.Column("priority", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_voice_improvement_tickets_status", "voice_improvement_tickets", ["status"])

    # ── Shared lookup tables ──────────────────────────────────────────────────
    op.create_table(
        "tenant_users",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tenant_users_tenant", "tenant_users", ["tenant_id"])

    op.create_table(
        "support_tickets",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), server_default="open", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_support_tickets_tenant_status", "support_tickets", ["tenant_id", "status"])

    op.create_table(
        "invoices",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(32), server_default="unpaid", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_invoices_tenant_status", "invoices", ["tenant_id", "status"])


def downgrade() -> None:
    for table in [
        "invoices",
        "support_tickets",
        "tenant_users",
        "voice_improvement_tickets",
        "voice_human_review_queue",
        "voice_war_room_incidents",
        "voice_recording_access_log",
        "voice_recording_governance",
        "voice_preferences",
        "voice_cost_caps",
        "voice_ab_tests",
        "voice_callback_slots",
        "voice_founder_busy_states",
        "voice_onboarding_sessions",
        "voice_compliance_guard_events",
        "voice_script_packs",
        "voice_alert_policies",
        "voice_screen_pops",
        "founder_chat_actions",
        "founder_chat_runs",
        "founder_chat_messages",
        "founder_chat_sessions",
    ]:
        op.drop_table(table)
