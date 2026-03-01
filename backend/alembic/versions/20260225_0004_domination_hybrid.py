"""Domination hybrid foundation (tenant tables + RLS + PostGIS)

Revision ID: 20260225_0004
Revises: 20260224_0003
Create Date: 2026-02-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "20260225_0004"
down_revision = "20260224_0003"
branch_labels = None
depends_on = None


TENANT_TABLES = [
    # Tenancy + Support
    "devices",
    "support_sessions",
    "feature_flags",
    # CAD + Ops
    "calls",
    "call_intake_answers",
    "dispatch_decisions",
    "units",
    "unit_status_events",
    "unit_locations",
    "crew_members",
    "crew_assignments",
    # Scheduling
    "shifts",
    "shift_instances",
    "availability_blocks",
    "time_off_requests",
    "bid_cycles",
    "shift_bids",
    "coverage_rulesets",
    "credentials",
    "credential_requirements",
    "schedule_audit_events",
    # CrewLink
    "pages",
    "page_targets",
    "page_responses",
    "escalation_policies",
    "on_call_rotations",
    # MDT
    "mdt_sessions",
    "mdt_offline_queue_items",
    # Fleet
    "obd_readings",
    "fleet_alerts",
    "camera_events",
    "maintenance_items",
    "inspection_checklists",
    # Weather
    "weather_tiles_cache",
    "weather_alerts",
    "aviation_weather_reports",
    # TransportLink
    "facilities",
    "facility_users",
    "facility_requests",
    "recurring_request_rules",
    "request_documents",
    # Documents + OCR + Signatures + Fax
    "documents",
    "document_extractions",
    "missing_document_tasks",
    "signature_requests",
    "signatures",
    "fax_jobs",
    "fax_events",
    # Billing + Office Ally
    "billing_cases",
    "claims",
    "edi_artifacts",
    "eras",
    "denials",
    "appeals",
    "billing_jobs",
    # Payments
    "pricing_plans",
    "usage_records",
    "stripe_webhook_receipts",
    "patient_payment_links",
    # Imports/Exports
    "import_batches",
    "import_mappings",
    "import_errors",
    "export_jobs",
    "export_artifacts",
    # AI
    "ai_runs",
    "ai_policies",
    # Fire
    "fire_incidents",
    "fire_reports",
    "fire_statements",
    "fire_apparatus",
    "fire_personnel_assignments",
    "fire_losses",
    "fire_actions_taken",
    # Compliance
    "nemsis_export_jobs",
    "nemsis_validation_results",
    "neris_export_jobs",
    "neris_validation_results",
    "governance_scores",
    # AR / Revenue Cycle
    "ar_accounts",
    "ar_charges",
    "ar_disputes",
    "ar_marker_sheets",
    "ar_markers",
    "ar_payment_plans",
    "ar_payments",
    "ar_statements",
    "billing_runs",
    "claim_documents",
    "claim_status_history",
    "ledger_entries",
    "submission_batches",
    "trip_debts",
    "trip_exports",
    "trip_postings",
    "trip_reject_imports",
    "trip_settings",
    # Cases + Payments + Pricebook
    "cases",
    "payments",
    "pricebook_items",
    "pricebooks",
    "patient_statements",
    # Events + Platform
    "event_reads",
    "platform_events",
    "document_events",
    "usage_events",
    # CMS / Collections
    "cms_gate_results",
    "collections_placements",
    "collections_settings",
    "collections_status_updates",
    "collections_vendor_profiles",
    # Compliance Packs (extended)
    "compliance_check_templates",
    "compliance_findings",
    "compliance_inspections",
    "compliance_pack_versions",
    "compliance_packs",
    "compliance_reports",
    "compliance_rules",
    # Documents / Legal
    "document_matches",
    "legal_documents",
    "legal_packets",
    "legal_sign_events",
    # Entitlements + Onboarding
    "entitlements",
    "onboarding_checklists",
    "onboarding_idempotency_keys",
    # Fire (extended)
    "fire_departments",
    "fire_incident_actions",
    "fire_incident_documents",
    "fire_incident_outcomes",
    "fire_incident_units",
    "fire_personnel",
    "fire_stations",
    # Formulary + Generated PDFs
    "formulary_items",
    "generated_pdfs",
    # HEMS (extended)
    "hems_acceptance_records",
    "hems_mission_events",
    "hems_risk_audits",
    "hems_weather_briefs",
    # Inspection
    "inspection_instances",
    "inspection_templates",
    # Inventory + Kit + Narc
    "compartment_items",
    "inventory_items",
    "inventory_transaction_lines",
    "inventory_transactions",
    "kit_compartments",
    "kit_templates",
    "kitlink_anomaly_flags",
    "kitlink_ocr_jobs",
    "kitlink_wizard_state",
    "narc_counts",
    "narc_discrepancies",
    "narc_kits",
    "narc_seals",
    "narc_waste_events",
    "unit_layout_kits",
    "unit_layouts",
    # Maintenance
    "maintenance_work_orders",
    # NEMSIS / NERIS (extended)
    "nemsis_audit_bundles",
    "nemsis_export_batches",
    "nemsis_extensions",
    "nemsis_state_rejections",
    "neris_compiled_rules",
    "neris_onboarding",
    "neris_pack_files",
    "neris_packs",
    "neris_value_set_definitions",
    "neris_value_set_items",
    # Readiness + Scheduling AI
    "ai_scheduling_drafts",
    "aircraft_readiness_events",
    "readiness_scores",
    # Rep Signatures + Builders
    "builders_rulesets",
    "rep_signatures",
    "stripe_bootstrap_log",
    # Stock
    "stock_balances",
    "stock_locations",
    # Support (extended)
    "support_escalations",
    "support_messages",
    "support_threads",
    # Tenant config
    "tenant_billing_config",
    "tenant_compliance_config",
    # Visibility
    "visibility_access_alerts",
    "visibility_anomaly_events",
    "visibility_approval_requests",
    "visibility_audit_log",
    "visibility_compliance_locks",
    "visibility_rules",
]


def _has_table(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _create_tenant_json_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
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
    op.execute(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f'CREATE POLICY "{name}_tenant_isolation" ON "{name}" USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid);'
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Extensions used by the platform
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    # Ensure base identity/audit tables exist (some repos already have these)
    if not _has_table(conn, "tenants"):
        op.create_table(
            "tenants",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_key", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
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
        op.create_index("ix_tenants_tenant_key", "tenants", ["tenant_key"], unique=True)

    if not _has_table(conn, "users"):
        op.create_table(
            "users",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        )
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)

    if not _has_table(conn, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("entity_name", sa.String(length=128), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "field_changes",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("correlation_id", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], unique=False)

    # Create tenant-scoped tables
    for t in TENANT_TABLES:
        if _has_table(conn, t):
            continue
        _create_tenant_json_table(t)

    # Specialize unit_locations with geography point for PostGIS
    if _has_table(conn, "unit_locations"):
        # add geometry column if not present
        cols = {c["name"] for c in sa.inspect(conn).get_columns("unit_locations")}
        if "location" not in cols:
            op.add_column(
                "unit_locations",
                sa.Column("location", postgresql.GEOGRAPHY("POINT", 4326), nullable=True),
            )

    # ICD10 reference (global)
    if not _has_table(conn, "icd10_versions"):
        op.create_table(
            "icd10_versions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("year", sa.Integer(), nullable=False, unique=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    if not _has_table(conn, "icd10_codes"):
        op.create_table(
            "icd10_codes",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("version_year", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=16), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
        )
        op.create_index("ix_icd10_codes_code", "icd10_codes", ["code"], unique=False)
        op.create_index(
            "ix_icd10_codes_year_code", "icd10_codes", ["version_year", "code"], unique=True
        )


def downgrade() -> None:
    # Downgrade is destructive; only remove tables created by this migration.
    conn = op.get_bind()
    for t in reversed(TENANT_TABLES):
        if _has_table(conn, t):
            op.drop_table(t)
    for t in ["icd10_codes", "icd10_versions"]:
        if _has_table(conn, t):
            op.drop_table(t)
