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
    "nemsis_export_jobs","nemsis_validation_results","neris_export_jobs","neris_validation_results","governance_scores",
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
