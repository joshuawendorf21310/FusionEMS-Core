"""founder copilot chat tables

Revision ID: 20260227_0005
Revises: 20260225_0004
Create Date: 2026-02-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260227_0005"
down_revision: Union[str, None] = "20260225_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "founder_chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("founder_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New session"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_chat_sessions_founder_user_id", "founder_chat_sessions", ["founder_user_id"])

    op.create_table(
        "founder_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_chat_messages_session_id", "founder_chat_messages", ["session_id"])
    op.create_foreign_key(
        "fk_founder_chat_messages_session_id",
        "founder_chat_messages", "founder_chat_sessions",
        ["session_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "founder_chat_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("plan_json", postgresql.JSONB(), nullable=True),
        sa.Column("release_gate_results_json", postgresql.JSONB(), nullable=True),
        sa.Column("diff_text", sa.Text(), nullable=True),
        sa.Column("diff_s3_key", sa.String(length=500), nullable=True),
        sa.Column("gh_run_id", sa.String(length=64), nullable=True),
        sa.Column("gh_run_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_chat_runs_session_id", "founder_chat_runs", ["session_id"])
    op.create_foreign_key(
        "fk_founder_chat_runs_session_id",
        "founder_chat_runs", "founder_chat_sessions",
        ["session_id"], ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "founder_chat_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_chat_actions_run_id", "founder_chat_actions", ["run_id"])
    op.create_foreign_key(
        "fk_founder_chat_actions_run_id",
        "founder_chat_actions", "founder_chat_runs",
        ["run_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("founder_chat_actions")
    op.drop_table("founder_chat_runs")
    op.drop_table("founder_chat_messages")
    op.drop_table("founder_chat_sessions")
