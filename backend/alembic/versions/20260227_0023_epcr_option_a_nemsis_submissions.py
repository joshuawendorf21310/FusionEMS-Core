"""ePCR Option A: typed columns, SHA256, retention indexes, nemsis_submission_results

Revision ID: 20260227_0023
Revises: 20260227_0022
Create Date: 2026-02-27

Adds to epcr_charts:
  - status        VARCHAR(32) typed column (mirrors data->chart_status, indexed)
  - submitted_at  TIMESTAMPTZ
  - deleted_at    TIMESTAMPTZ  (soft-delete / retention gate)
  - legal_hold    BOOLEAN DEFAULT FALSE
  - schema_version VARCHAR(16) DEFAULT '3.5'
  - sha256_submitted  VARCHAR(64)  (JCS canonical hash set on submit)
  - case_id       UUID nullable  (FK reference stored for index; value lives in data too)

Adds to epcr_event_log:
  - deleted_at  TIMESTAMPTZ

Adds to audit_logs:
  - deleted_at  TIMESTAMPTZ (soft-delete support for retention sweep)

Creates:
  - nemsis_submission_results  (state submission tracking + S3 keys + status history)
  - nemsis_submission_status_history  (append-only log per submission)

Creates required indexes per spec (partial, no broad GIN).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260227_0023"
down_revision = "20260227_0022"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    cols = {c["name"] for c in sa.inspect(conn).get_columns(table)}
    return column in cols


def _index_exists(conn, name: str) -> bool:
    return name in {i["name"] for i in sa.inspect(conn).get_indexes("epcr_charts") if "name" in i}


def _table_exists(conn, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # 1. epcr_charts — add typed/retention columns                        #
    # ------------------------------------------------------------------ #
    for col_name, col_def in [
        ("status", sa.Column("status", sa.String(32), nullable=True)),
        ("submitted_at", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)),
        ("deleted_at", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)),
        (
            "legal_hold",
            sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        ),
        (
            "schema_version",
            sa.Column(
                "schema_version", sa.String(16), nullable=False, server_default=sa.text("'3.5'")
            ),
        ),
        ("sha256_submitted", sa.Column("sha256_submitted", sa.String(64), nullable=True)),
        ("case_id", sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True)),
    ]:
        if not _col_exists(conn, "epcr_charts", col_name):
            op.add_column("epcr_charts", col_def)

    # Back-fill status from JSONB data for existing rows
    conn.execute(
        sa.text("UPDATE epcr_charts SET status = data->>'chart_status' WHERE status IS NULL")
    )

    # ------------------------------------------------------------------ #
    # 2. epcr_charts — required partial indexes                           #
    # ------------------------------------------------------------------ #
    indexes = [
        (
            "ix_epcr_charts_tenant_status_updated",
            "CREATE INDEX IF NOT EXISTS ix_epcr_charts_tenant_status_updated "
            "ON epcr_charts (tenant_id, status, updated_at DESC) "
            "WHERE deleted_at IS NULL",
        ),
        (
            "ix_epcr_charts_tenant_submitted_at",
            "CREATE INDEX IF NOT EXISTS ix_epcr_charts_tenant_submitted_at "
            "ON epcr_charts (tenant_id, submitted_at DESC) "
            "WHERE deleted_at IS NULL AND submitted_at IS NOT NULL",
        ),
        (
            "ix_epcr_charts_tenant_case_id",
            "CREATE INDEX IF NOT EXISTS ix_epcr_charts_tenant_case_id "
            "ON epcr_charts (tenant_id, case_id) "
            "WHERE deleted_at IS NULL AND case_id IS NOT NULL",
        ),
        (
            "ix_epcr_charts_tenant_deleted_at",
            "CREATE INDEX IF NOT EXISTS ix_epcr_charts_tenant_deleted_at "
            "ON epcr_charts (tenant_id, deleted_at DESC) "
            "WHERE deleted_at IS NOT NULL",
        ),
        (
            "ix_epcr_charts_tenant_legal_hold",
            "CREATE INDEX IF NOT EXISTS ix_epcr_charts_tenant_legal_hold "
            "ON epcr_charts (tenant_id, legal_hold, updated_at DESC) "
            "WHERE legal_hold = TRUE",
        ),
    ]
    for _name, ddl in indexes:
        conn.execute(sa.text(ddl))

    # ------------------------------------------------------------------ #
    # 3. epcr_event_log — add deleted_at for retention                   #
    # ------------------------------------------------------------------ #
    if not _col_exists(conn, "epcr_event_log", "deleted_at"):
        op.add_column(
            "epcr_event_log", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    conn.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_epcr_event_log_tenant_deleted "
            "ON epcr_event_log (tenant_id, deleted_at DESC) WHERE deleted_at IS NOT NULL"
        )
    )

    # ------------------------------------------------------------------ #
    # 4. audit_logs — add deleted_at for retention                        #
    # ------------------------------------------------------------------ #
    if not _col_exists(conn, "audit_logs", "deleted_at"):
        op.add_column(
            "audit_logs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )

    # ------------------------------------------------------------------ #
    # 5. nemsis_submission_results                                         #
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, "nemsis_submission_results"):
        op.create_table(
            "nemsis_submission_results",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("submission_id", sa.String(128), nullable=True),
            sa.Column("state_code", sa.String(8), nullable=False),
            sa.Column("endpoint_url", sa.String(512), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("xml_s3_bucket", sa.String(255), nullable=True),
            sa.Column("xml_s3_key", sa.String(1024), nullable=True),
            sa.Column("ack_s3_bucket", sa.String(255), nullable=True),
            sa.Column("ack_s3_key", sa.String(1024), nullable=True),
            sa.Column("response_s3_bucket", sa.String(255), nullable=True),
            sa.Column("response_s3_key", sa.String(1024), nullable=True),
            sa.Column("sha256_payload", sa.String(64), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
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
        op.create_index("ix_nsr_tenant_id", "nemsis_submission_results", ["tenant_id"])
        op.create_index("ix_nsr_chart_id", "nemsis_submission_results", ["chart_id"])
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_nsr_tenant_chart "
                "ON nemsis_submission_results (tenant_id, chart_id, created_at DESC)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_nsr_tenant_status "
                "ON nemsis_submission_results (tenant_id, status, submitted_at DESC) "
                "WHERE deleted_at IS NULL"
            )
        )
        op.execute('ALTER TABLE "nemsis_submission_results" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            'CREATE POLICY "nemsis_submission_results_tenant_isolation" '
            'ON "nemsis_submission_results" '
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
        )

    # ------------------------------------------------------------------ #
    # 6. nemsis_submission_status_history  (append-only)                  #
    # ------------------------------------------------------------------ #
    if not _table_exists(conn, "nemsis_submission_status_history"):
        op.create_table(
            "nemsis_submission_status_history",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("from_status", sa.String(32), nullable=True),
            sa.Column("to_status", sa.String(32), nullable=False),
            sa.Column("actor", sa.String(255), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("s3_bucket", sa.String(255), nullable=True),
            sa.Column("s3_key", sa.String(1024), nullable=True),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
            ),
        )
        op.create_index("ix_nssh_tenant_id", "nemsis_submission_status_history", ["tenant_id"])
        op.create_index(
            "ix_nssh_submission_id", "nemsis_submission_status_history", ["submission_id"]
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_nssh_submission_occurred "
                "ON nemsis_submission_status_history (submission_id, occurred_at DESC)"
            )
        )
        op.execute('ALTER TABLE "nemsis_submission_status_history" ENABLE ROW LEVEL SECURITY;')
        op.execute(
            'CREATE POLICY "nemsis_submission_status_history_tenant_isolation" '
            'ON "nemsis_submission_status_history" '
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
        )


def downgrade() -> None:
    conn = op.get_bind()
    for t in ["nemsis_submission_status_history", "nemsis_submission_results"]:
        if t in sa.inspect(conn).get_table_names():
            op.drop_table(t)
    for col in [
        "status",
        "submitted_at",
        "deleted_at",
        "legal_hold",
        "schema_version",
        "sha256_submitted",
        "case_id",
    ]:
        try:
            op.drop_column("epcr_charts", col)
        except Exception:
            pass
    try:
        op.drop_column("epcr_event_log", "deleted_at")
    except Exception:
        pass
    try:
        op.drop_column("audit_logs", "deleted_at")
    except Exception:
        pass
