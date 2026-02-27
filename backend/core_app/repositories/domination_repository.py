from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Whitelist of tenant-scoped tables created by domination migration.
TENANT_TABLES: set[str] = {
    "devices","support_sessions","feature_flags",
    "calls","call_intake_answers","dispatch_decisions","units","unit_status_events","unit_locations","crew_members","crew_assignments",
    "shifts","shift_instances","availability_blocks","time_off_requests","bid_cycles","shift_bids","coverage_rulesets","credentials","credential_requirements","schedule_audit_events",
    "pages","page_targets","page_responses","escalation_policies","on_call_rotations",
    "mdt_sessions","mdt_offline_queue_items",
    "obd_readings","fleet_alerts","camera_events","maintenance_items","inspection_checklists",
    "weather_tiles_cache","weather_alerts","aviation_weather_reports",
    "facilities","facility_users","facility_requests","recurring_request_rules","request_documents",
    "documents","document_extractions","missing_document_tasks","signature_requests","signatures","fax_jobs","fax_events",
    "billing_cases","claims","edi_artifacts","eras","denials","appeals","billing_jobs",
    "pricing_plans","usage_records","stripe_webhook_receipts","lob_webhook_receipts","patient_payment_links",
    "import_batches","import_mappings","import_errors","export_jobs","export_artifacts",
    "ai_runs","ai_policies",
    "fire_incidents","fire_reports","fire_statements","fire_apparatus","fire_personnel_assignments","fire_losses","fire_actions_taken",
    "fire_departments","fire_stations","fire_personnel","fire_incident_units","fire_incident_actions","fire_incident_outcomes",
    "fire_incident_documents",
    "neris_onboarding",
    "neris_packs","neris_pack_files","neris_value_set_definitions","neris_value_set_items","neris_compiled_rules",
    "nemsis_export_jobs","nemsis_validation_results","neris_export_jobs","neris_validation_results","governance_scores",
    "nemsis_resource_packs","nemsis_pack_files","nemsis_ai_explanations","nemsis_cs_scenarios","nemsis_patch_tasks",
    "epcr_charts","epcr_event_log","epcr_ai_outputs","epcr_ocr_jobs","epcr_capture_sessions",
    "epcr_workflow_templates","epcr_customization_rules","epcr_form_layouts","epcr_agency_branding",
    "epcr_picklist_items","epcr_chart_workflow_blocks","epcr_completeness_snapshots","epcr_sync_conflicts",
    "telnyx_webhook_receipts",
    "builders_rulesets",
    "builders_workflows",
    "templates",
    "auth_rep_sessions","authorized_reps","rep_documents",
    "track_tokens","track_events",
    "payments",
    "fire_preplans","fire_hydrants",
    "lob_letters",
    "webhook_dlq",
    "tenant_subscriptions",
    "tenant_provisioning_events",
    "tenants",
    "legal_packets","legal_documents","legal_sign_events","document_events",
    "submission_batches","claim_status_history","claim_documents",
    "document_matches","generated_pdfs",
    "support_threads","support_messages","support_escalations",
    "platform_events","event_reads","onboarding_idempotency_keys",
    "cases","cms_gate_results","hems_acceptance_records","hems_weather_briefs","hems_risk_audits","aircraft_readiness_events","maintenance_work_orders","inspection_templates","inspection_instances","readiness_scores","ai_scheduling_drafts",
    "ar_accounts","ar_charges","ar_payments","ar_payment_plans","ar_disputes","ar_statements","collections_vendor_profiles","collections_placements","collections_status_updates","collections_settings",
    "trip_settings","trip_debts","trip_exports","trip_reject_imports","trip_postings",
    "pricebooks","pricebook_items","ledger_entries","usage_events","tenant_billing_config","billing_runs","stripe_bootstrap_log","entitlements",
    "inventory_items","formulary_items","kit_templates","kit_compartments","compartment_items",
    "unit_layouts","unit_layout_kits","ar_markers","ar_marker_sheets",
    "inventory_transactions","inventory_transaction_lines","stock_locations","stock_balances",
    "narc_kits","narc_seals","narc_counts","narc_waste_events","narc_discrepancies",
    "kitlink_ocr_jobs","kitlink_anomaly_flags","compliance_packs","compliance_check_templates",
    "compliance_inspections","compliance_findings","kitlink_wizard_state",
    "compliance_pack_versions","compliance_rules","compliance_reports","tenant_compliance_config",
    "hems_mission_events","rep_signatures","auth_rep_sessions","authorized_reps","rep_documents","billing_cases","patient_statements",
    "appeal_drafts","baa_signatures","billing_alert_thresholds","bulk_generation_jobs","claim_events","conversion_events","denial_predictions","device_registrations","emergency_locks","geo_alerts","global_variables","incident_postmortems","incidents","lead_scores","mobile_alerts","mobile_errors","mobile_sessions","nemsis_audit_bundles","nemsis_export_batches","nemsis_extensions","nemsis_state_rejections","ocr_captures","offline_sync_jobs","onboarding_checklists","payer_follow_ups","production_change_approvals","proposals","push_notifications","pwa_deployments","pwa_installs","pwa_manifest_updates","recovery_simulations","roi_funnel_scenarios","roi_share_links","scheduled_deliveries","self_healing_actions","self_healing_rules","shift_swaps","system_alerts","template_ab_tests","template_downloads","template_renders","template_secure_links","template_versions","user_credentials","visibility_access_alerts","visibility_anomaly_events","visibility_approval_requests","visibility_audit_log","visibility_compliance_locks","visibility_rules",
    "founder_chat_sessions","founder_chat_messages","founder_chat_runs","founder_chat_actions","voice_screen_pops","voice_alert_policies","voice_script_packs","voice_compliance_guard_events","voice_onboarding_sessions","voice_founder_busy_states","voice_callback_slots","voice_ab_tests","voice_cost_caps","voice_preferences","voice_recording_governance","voice_recording_access_log","voice_war_room_incidents","voice_human_review_queue","voice_improvement_tickets","tenant_users","support_tickets","invoices",
}


class DominationRepository:
    def __init__(self, db: Session, *, table: str) -> None:
        if table not in TENANT_TABLES:
            raise ValueError(f"Unsupported table: {table}")
        self.db = db
        self.table = table

    def create(self, *, tenant_id: uuid.UUID, data: dict[str, Any]) -> dict[str, Any]:
        sql = text(f"""
            INSERT INTO {self.table} (tenant_id, data)
            VALUES (:tenant_id, CAST(:data AS jsonb))
            RETURNING id, tenant_id, data, version, created_at, updated_at
        """)
        row = self.db.execute(sql, {"tenant_id": str(tenant_id), "data": json_dumps(data)}).mappings().one()
        return dict(row)

    def get(self, *, tenant_id: uuid.UUID, record_id: uuid.UUID) -> dict[str, Any] | None:
        sql = text(f"""
            SELECT id, tenant_id, data, version, created_at, updated_at, deleted_at
            FROM {self.table}
            WHERE tenant_id = :tenant_id AND id = :id AND deleted_at IS NULL
        """)
        row = self.db.execute(sql, {"tenant_id": str(tenant_id), "id": str(record_id)}).mappings().first()
        return dict(row) if row else None

    def list(self, *, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        sql = text(f"""
            SELECT id, tenant_id, data, version, created_at, updated_at
            FROM {self.table}
            WHERE tenant_id = :tenant_id AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = self.db.execute(sql, {"tenant_id": str(tenant_id), "limit": limit, "offset": offset}).mappings().all()
        return [dict(r) for r in rows]

    _SAFE_FIELD_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')

    def list_raw_by_field(self, field: str, value: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self._SAFE_FIELD_RE.match(field):
            raise ValueError(f"Invalid field name: {field!r}")
        sql = text(
            f"SELECT id, tenant_id, data, version, created_at, updated_at "
            f"FROM {self.table} "
            f"WHERE data->>:field = :value AND deleted_at IS NULL "
            f"ORDER BY created_at DESC LIMIT :limit"
        )
        rows = self.db.execute(sql, {"field": field, "value": value, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

    def update(self, *, tenant_id: uuid.UUID, record_id: uuid.UUID, expected_version: int, patch: dict[str, Any]) -> dict[str, Any] | None:
        # optimistic concurrency: update only if version matches.
        sql = text(f"""
            UPDATE {self.table}
            SET data = data || CAST(:patch AS jsonb),
                version = version + 1,
                updated_at = now()
            WHERE tenant_id = :tenant_id AND id = :id AND deleted_at IS NULL AND version = :expected_version
            RETURNING id, tenant_id, data, version, created_at, updated_at
        """)
        row = self.db.execute(sql, {"tenant_id": str(tenant_id), "id": str(record_id), "expected_version": expected_version, "patch": json_dumps(patch)}).mappings().first()
        return dict(row) if row else None

    def soft_delete(self, *, tenant_id: uuid.UUID, record_id: uuid.UUID) -> bool:
        sql = text(f"""
            UPDATE {self.table}
            SET deleted_at = now(), updated_at = now()
            WHERE tenant_id = :tenant_id AND id = :id AND deleted_at IS NULL
        """)
        res = self.db.execute(sql, {"tenant_id": str(tenant_id), "id": str(record_id)})
        return res.rowcount > 0


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
