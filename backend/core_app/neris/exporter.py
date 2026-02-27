from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

import boto3

from core_app.documents.s3_storage import put_bytes, presign_get, default_exports_bucket
from core_app.neris.validator import NERISValidator
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

EXPORT_S3_PREFIX = "neris/exports"


class NERISExporter:
    def __init__(self, db, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id
        self.db = db

    def build_entity_payload(self, department_id: uuid.UUID) -> dict[str, Any]:
        dept = self.svc.repo("fire_departments").get(tenant_id=self.tenant_id, record_id=department_id)
        if not dept:
            raise ValueError("department_not_found")
        dd = dept.get("data") or {}

        stations = self.svc.repo("fire_stations").list(tenant_id=self.tenant_id, limit=100)
        stations = [s for s in stations if (s.get("data") or {}).get("department_id") == str(department_id)]

        apparatus = self.svc.repo("fire_apparatus").list(tenant_id=self.tenant_id, limit=200)
        apparatus = [a for a in apparatus if (a.get("data") or {}).get("department_id") == str(department_id)]

        return {
            "department": {
                "id": str(department_id),
                "name": dd.get("name", ""),
                "state": dd.get("state", "WI"),
                "primary_contact_name": dd.get("primary_contact_name", ""),
                "primary_contact_email": dd.get("primary_contact_email", ""),
                "primary_contact_phone": dd.get("primary_contact_phone", ""),
                "reporting_mode": "RMS",
                "stations": [
                    {
                        "id": str(s["id"]),
                        "name": (s.get("data") or {}).get("name", ""),
                        "address": (s.get("data") or {}).get("address_json", {}),
                    }
                    for s in stations
                ],
                "apparatus": [
                    {
                        "id": str(a["id"]),
                        "unit_id": (a.get("data") or {}).get("unit_id", ""),
                        "unit_type_code": (a.get("data") or {}).get("unit_type_code", ""),
                    }
                    for a in apparatus
                ],
            }
        }

    def build_incident_payload(self, incident: dict[str, Any]) -> dict[str, Any]:
        idata = incident.get("data") or {}
        inc_id = str(incident["id"])

        units = self.svc.repo("fire_incident_units").list(tenant_id=self.tenant_id, limit=50)
        units = [u for u in units if (u.get("data") or {}).get("incident_id") == inc_id]

        actions = self.svc.repo("fire_incident_actions").list(tenant_id=self.tenant_id, limit=50)
        actions = [a for a in actions if (a.get("data") or {}).get("incident_id") == inc_id]

        outcomes_list = self.svc.repo("fire_incident_outcomes").list(tenant_id=self.tenant_id, limit=5)
        outcomes_list = [o for o in outcomes_list if (o.get("data") or {}).get("incident_id") == inc_id]
        outcomes = (outcomes_list[0].get("data") or {}).get("outcomes_json", {}) if outcomes_list else {}

        return {
            "incident": {
                "id": inc_id,
                "incident_number": idata.get("incident_number", ""),
                "start_datetime": idata.get("start_datetime", ""),
                "end_datetime": idata.get("end_datetime"),
                "type_code": idata.get("incident_type_code", ""),
                "location": idata.get("location_json", {}),
                "property_use_code": idata.get("property_use_code"),
                "neris_pack_id": idata.get("neris_pack_id"),
                "units": [
                    {
                        "unit_id": (u.get("data") or {}).get("unit_id", ""),
                        "apparatus_id": (u.get("data") or {}).get("apparatus_id", ""),
                        "arrival_datetime": (u.get("data") or {}).get("arrival_datetime"),
                        "departure_datetime": (u.get("data") or {}).get("departure_datetime"),
                    }
                    for u in units
                ],
                "actions": [
                    {
                        "action_code": (a.get("data") or {}).get("action_code", ""),
                        "action_datetime": (a.get("data") or {}).get("action_datetime"),
                    }
                    for a in actions
                ],
                "outcomes": outcomes,
            }
        }

    async def generate_bundle(
        self,
        department_id: uuid.UUID,
        incident_ids: list[uuid.UUID],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        entity_payload = self.build_entity_payload(department_id)
        incidents_payload = []
        for iid in incident_ids:
            inc = self.svc.repo("fire_incidents").get(tenant_id=self.tenant_id, record_id=iid)
            if inc:
                incidents_payload.append(self.build_incident_payload(inc))

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        metadata = {
            "tenant_id": str(self.tenant_id),
            "department_id": str(department_id),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "record_counts": {"incidents": len(incidents_payload)},
            "format_version": "neris-wi-rms-v1",
        }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("entity.json", json.dumps(entity_payload, indent=2))
            zf.writestr("incidents.json", json.dumps(incidents_payload, indent=2))
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        zip_bytes = zip_buffer.getvalue()

        bucket = default_exports_bucket()
        s3_key = f"{EXPORT_S3_PREFIX}/{self.tenant_id}/{department_id}/{ts}/bundle.zip"
        if bucket:
            put_bytes(bucket=bucket, key=s3_key, content=zip_bytes, content_type="application/zip")

        export_record = await self.svc.create(
            table="neris_export_jobs",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "department_id": str(department_id),
                "status": "complete",
                "s3_key": s3_key,
                "bucket": bucket or "",
                "incident_count": len(incidents_payload),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "neris-wi-rms-v1",
            },
            correlation_id=correlation_id,
        )

        download_url = presign_get(bucket=bucket, key=s3_key, expires_seconds=900) if bucket else None
        return {
            "export_id": str(export_record["id"]),
            "s3_key": s3_key,
            "incident_count": len(incidents_payload),
            "download_url": download_url,
        }
