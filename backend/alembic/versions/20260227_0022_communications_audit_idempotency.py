"""Raw SQL tables: communications, document_audit_events, tenant_provisioning_idempotency

Revision ID: 20260227_0022
Revises: 20260227_0021
Create Date: 2026-02-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260227_0022"
down_revision = "20260227_0021"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "communications"):
        op.create_table(
            "communications",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("channel", sa.String(length=64), nullable=False),
            sa.Column("direction", sa.String(length=16), nullable=False),
            sa.Column(
                "data",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.execute('ALTER TABLE "communications" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            'CREATE POLICY "communications_tenant_isolation" ON "communications" '
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
        )

    if not _has_table(conn, "document_audit_events"):
        op.create_table(
            "document_audit_events",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("entity_type", sa.String(length=128), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column(
                "meta",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_document_audit_events_tenant_id", "document_audit_events", ["tenant_id"]
        )
        op.create_index(
            "ix_document_audit_events_entity_id", "document_audit_events", ["entity_id"]
        )

    if not _has_table(conn, "tenant_provisioning_idempotency"):
        op.create_table(
            "tenant_provisioning_idempotency",
            sa.Column("application_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_tenant_provisioning_idempotency_tenant_id",
            "tenant_provisioning_idempotency",
            ["tenant_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    for t in ["tenant_provisioning_idempotency", "document_audit_events", "communications"]:
        if _has_table(conn, t):
            op.drop_table(t)
