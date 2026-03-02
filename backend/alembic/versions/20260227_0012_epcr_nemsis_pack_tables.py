"""ePCR + NEMSIS pack tables

Revision ID: 20260227_0012
Revises: 20260227_0011
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260227_0012"
down_revision = "20260227_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nemsis_resource_packs",
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
    op.create_index("ix_nemsis_resource_packs_tenant_id", "nemsis_resource_packs", ["tenant_id"])
    op.create_index(
        "ix_nemsis_resource_packs_data",
        "nemsis_resource_packs",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "nemsis_pack_files",
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
    op.create_index("ix_nemsis_pack_files_tenant_id", "nemsis_pack_files", ["tenant_id"])
    op.create_index(
        "ix_nemsis_pack_files_data", "nemsis_pack_files", [sa.text("data")], postgresql_using="gin"
    )

    op.create_table(
        "nemsis_ai_explanations",
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
    op.create_index("ix_nemsis_ai_explanations_tenant_id", "nemsis_ai_explanations", ["tenant_id"])
    op.create_index(
        "ix_nemsis_ai_explanations_data",
        "nemsis_ai_explanations",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "nemsis_cs_scenarios",
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
    op.create_index("ix_nemsis_cs_scenarios_tenant_id", "nemsis_cs_scenarios", ["tenant_id"])
    op.create_index(
        "ix_nemsis_cs_scenarios_data",
        "nemsis_cs_scenarios",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "nemsis_patch_tasks",
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
    op.create_index("ix_nemsis_patch_tasks_tenant_id", "nemsis_patch_tasks", ["tenant_id"])
    op.create_index(
        "ix_nemsis_patch_tasks_data",
        "nemsis_patch_tasks",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_charts",
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
    op.create_index("ix_epcr_charts_tenant_id", "epcr_charts", ["tenant_id"])
    op.create_index("ix_epcr_charts_data", "epcr_charts", [sa.text("data")], postgresql_using="gin")

    op.create_table(
        "epcr_event_log",
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
    op.create_index("ix_epcr_event_log_tenant_id", "epcr_event_log", ["tenant_id"])
    op.create_index(
        "ix_epcr_event_log_data", "epcr_event_log", [sa.text("data")], postgresql_using="gin"
    )

    op.create_table(
        "epcr_ai_outputs",
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
    op.create_index("ix_epcr_ai_outputs_tenant_id", "epcr_ai_outputs", ["tenant_id"])
    op.create_index(
        "ix_epcr_ai_outputs_data", "epcr_ai_outputs", [sa.text("data")], postgresql_using="gin"
    )

    op.create_table(
        "epcr_ocr_jobs",
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
    op.create_index("ix_epcr_ocr_jobs_tenant_id", "epcr_ocr_jobs", ["tenant_id"])
    op.create_index(
        "ix_epcr_ocr_jobs_data", "epcr_ocr_jobs", [sa.text("data")], postgresql_using="gin"
    )

    op.create_table(
        "epcr_capture_sessions",
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
    op.create_index("ix_epcr_capture_sessions_tenant_id", "epcr_capture_sessions", ["tenant_id"])
    op.create_index(
        "ix_epcr_capture_sessions_data",
        "epcr_capture_sessions",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_workflow_templates",
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
    op.create_index(
        "ix_epcr_workflow_templates_tenant_id", "epcr_workflow_templates", ["tenant_id"]
    )
    op.create_index(
        "ix_epcr_workflow_templates_data",
        "epcr_workflow_templates",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_customization_rules",
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
    op.create_index(
        "ix_epcr_customization_rules_tenant_id", "epcr_customization_rules", ["tenant_id"]
    )
    op.create_index(
        "ix_epcr_customization_rules_data",
        "epcr_customization_rules",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_form_layouts",
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
    op.create_index("ix_epcr_form_layouts_tenant_id", "epcr_form_layouts", ["tenant_id"])
    op.create_index(
        "ix_epcr_form_layouts_data", "epcr_form_layouts", [sa.text("data")], postgresql_using="gin"
    )

    op.create_table(
        "epcr_agency_branding",
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
    op.create_index("ix_epcr_agency_branding_tenant_id", "epcr_agency_branding", ["tenant_id"])
    op.create_index(
        "ix_epcr_agency_branding_data",
        "epcr_agency_branding",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_picklist_items",
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
    op.create_index("ix_epcr_picklist_items_tenant_id", "epcr_picklist_items", ["tenant_id"])
    op.create_index(
        "ix_epcr_picklist_items_data",
        "epcr_picklist_items",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_chart_workflow_blocks",
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
    op.create_index(
        "ix_epcr_chart_workflow_blocks_tenant_id", "epcr_chart_workflow_blocks", ["tenant_id"]
    )
    op.create_index(
        "ix_epcr_chart_workflow_blocks_data",
        "epcr_chart_workflow_blocks",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_completeness_snapshots",
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
    op.create_index(
        "ix_epcr_completeness_snapshots_tenant_id", "epcr_completeness_snapshots", ["tenant_id"]
    )
    op.create_index(
        "ix_epcr_completeness_snapshots_data",
        "epcr_completeness_snapshots",
        [sa.text("data")],
        postgresql_using="gin",
    )

    op.create_table(
        "epcr_sync_conflicts",
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
    op.create_index("ix_epcr_sync_conflicts_tenant_id", "epcr_sync_conflicts", ["tenant_id"])
    op.create_index(
        "ix_epcr_sync_conflicts_data",
        "epcr_sync_conflicts",
        [sa.text("data")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("epcr_sync_conflicts")
    op.drop_table("epcr_completeness_snapshots")
    op.drop_table("epcr_chart_workflow_blocks")
    op.drop_table("epcr_picklist_items")
    op.drop_table("epcr_agency_branding")
    op.drop_table("epcr_form_layouts")
    op.drop_table("epcr_customization_rules")
    op.drop_table("epcr_workflow_templates")
    op.drop_table("epcr_capture_sessions")
    op.drop_table("epcr_ocr_jobs")
    op.drop_table("epcr_ai_outputs")
    op.drop_table("epcr_event_log")
    op.drop_table("epcr_charts")
    op.drop_table("nemsis_patch_tasks")
    op.drop_table("nemsis_cs_scenarios")
    op.drop_table("nemsis_ai_explanations")
    op.drop_table("nemsis_pack_files")
    op.drop_table("nemsis_resource_packs")
