from __future__ import annotations

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
import yaml

from core_app.documents.s3_storage import put_bytes, default_docs_bucket
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

PACK_S3_PREFIX = "neris/packs"


class NERISPackCompiler:
    """
    Reads raw pack files from S3 (stored by import worker), parses YAML modules
    and CSV/YAML value sets, produces canonical rules_json for ENTITY and INCIDENT,
    stores into neris_compiled_rules + neris_value_set_definitions/items.
    """

    def __init__(self, db, publisher: EventPublisher, tenant_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    async def compile_pack(self, pack_id: uuid.UUID, correlation_id: str | None = None) -> dict[str, Any]:
        pack = self.svc.repo("neris_packs").get(tenant_id=self.tenant_id, record_id=pack_id)
        if not pack:
            raise ValueError("pack_not_found")

        pack_files = self.svc.repo("neris_pack_files").list(tenant_id=self.tenant_id, limit=500)
        pack_files = [f for f in pack_files if (f.get("data") or {}).get("pack_id") == str(pack_id)]

        s3 = boto3.client("s3")
        bucket = default_docs_bucket() or os.environ.get("S3_BUCKET_DOCS", "")
        raw_files: dict[str, bytes] = {}
        for pf in pack_files:
            pfd = pf.get("data") or {}
            s3_key = pfd.get("s3_key_raw", "")
            path = pfd.get("path", "")
            if s3_key and bucket:
                try:
                    obj = s3.get_object(Bucket=bucket, Key=s3_key)
                    raw_files[path] = obj["Body"].read()
                except Exception:
                    pass

        value_sets = self._parse_value_sets(raw_files)
        entity_rules = self._build_entity_rules(raw_files, value_sets)
        incident_rules = self._build_incident_rules(raw_files, value_sets)

        for vs_code, vs_data in value_sets.items():
            vs_def = await self.svc.create(
                table="neris_value_set_definitions",
                tenant_id=self.tenant_id,
                actor_user_id=self.actor_user_id,
                data={
                    "pack_id": str(pack_id),
                    "code": vs_code,
                    "name": vs_data.get("name", vs_code),
                    "version": vs_data.get("version", ""),
                    "source_path": vs_data.get("source_path", ""),
                },
                correlation_id=correlation_id,
            )
            for item in vs_data.get("items", []):
                await self.svc.create(
                    table="neris_value_set_items",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data={
                        "definition_id": str(vs_def["id"]),
                        "pack_id": str(pack_id),
                        "value_code": item.get("code", ""),
                        "display": item.get("display", ""),
                        "deprecated": item.get("deprecated", False),
                        "metadata_json": item.get("metadata", {}),
                    },
                    correlation_id=correlation_id,
                )

        for entity_type, rules in [("ENTITY", entity_rules), ("INCIDENT", incident_rules)]:
            rules_bytes = json.dumps(rules, indent=2).encode()
            s3_key = f"{PACK_S3_PREFIX}/{pack_id}/compiled/rules_{entity_type.lower()}.json"
            if bucket:
                put_bytes(bucket=bucket, key=s3_key, content=rules_bytes, content_type="application/json")

            await self.svc.create(
                table="neris_compiled_rules",
                tenant_id=self.tenant_id,
                actor_user_id=self.actor_user_id,
                data={
                    "pack_id": str(pack_id),
                    "entity_type": entity_type,
                    "rules_json": rules,
                    "schema_version": (pack.get("data") or {}).get("source_ref", ""),
                    "compiled_at": datetime.now(timezone.utc).isoformat(),
                    "s3_key": s3_key,
                },
                correlation_id=correlation_id,
            )

        pdata = dict(pack.get("data") or {})
        pdata["status"] = "staged"
        pdata["compiled"] = True
        pdata["compiled_at"] = datetime.now(timezone.utc).isoformat()
        await self.svc.update(
            table="neris_packs",
            tenant_id=self.tenant_id,
            record_id=pack_id,
            actor_user_id=self.actor_user_id,
            patch=pdata,
            expected_version=pack.get("version", 1),
            correlation_id=correlation_id,
        )
        return {"pack_id": str(pack_id), "entity_rules_fields": len(entity_rules.get("sections", [])), "incident_rules_fields": len(incident_rules.get("sections", []))}

    def _parse_value_sets(self, raw_files: dict[str, bytes]) -> dict[str, Any]:
        value_sets: dict[str, Any] = {}
        for path, content in raw_files.items():
            path_lower = path.lower()
            if "valueset" in path_lower or "value_set" in path_lower or "values" in path_lower:
                try:
                    if path_lower.endswith(".csv"):
                        reader = csv.DictReader(io.StringIO(content.decode("utf-8", errors="replace")))
                        rows = list(reader)
                        if rows:
                            code_field = next((k for k in rows[0] if "code" in k.lower()), None)
                            display_field = next((k for k in rows[0] if "description" in k.lower() or "display" in k.lower() or "name" in k.lower()), None)
                            vs_code = os.path.splitext(os.path.basename(path))[0].upper().replace("-", "_").replace(" ", "_")
                            items = []
                            for r in rows:
                                c = r.get(code_field, "").strip() if code_field else ""
                                d = r.get(display_field, "").strip() if display_field else c
                                if c:
                                    items.append({"code": c, "display": d})
                            value_sets[vs_code] = {"name": vs_code, "source_path": path, "items": items}
                    elif path_lower.endswith((".yml", ".yaml")):
                        parsed = yaml.safe_load(content.decode("utf-8", errors="replace")) or {}
                        if isinstance(parsed, dict):
                            vs_code = parsed.get("code") or parsed.get("id") or os.path.splitext(os.path.basename(path))[0].upper()
                            items_raw = parsed.get("values") or parsed.get("items") or []
                            items = []
                            for item in items_raw:
                                if isinstance(item, dict):
                                    items.append({"code": str(item.get("code") or item.get("value") or ""), "display": str(item.get("display") or item.get("description") or item.get("name") or "")})
                                elif isinstance(item, str):
                                    items.append({"code": item, "display": item})
                            value_sets[str(vs_code).upper()] = {"name": str(vs_code), "source_path": path, "items": items}
                except Exception:
                    pass
        if not value_sets:
            value_sets = _wi_default_value_sets()
        return value_sets

    def _build_entity_rules(self, raw_files: dict[str, bytes], value_sets: dict[str, Any]) -> dict[str, Any]:
        return {
            "entity_type": "ENTITY",
            "sections": [
                {
                    "id": "department.identity",
                    "label": "Department Identity",
                    "fields": [
                        {"path": "department.name", "label": "Department Name", "type": "string", "required": True},
                        {"path": "department.state", "label": "State", "type": "string", "required": True},
                        {"path": "department.primary_contact_name", "label": "Primary Contact Name", "type": "string", "required": True},
                        {"path": "department.primary_contact_email", "label": "Primary Contact Email", "type": "email", "required": True},
                        {"path": "department.primary_contact_phone", "label": "Primary Contact Phone", "type": "string", "required": True},
                    ],
                },
                {
                    "id": "department.stations",
                    "label": "Fire Stations",
                    "fields": [
                        {"path": "department.stations[].name", "label": "Station Name", "type": "string", "required": True},
                        {"path": "department.stations[].address", "label": "Station Address", "type": "object", "required": True},
                    ],
                },
                {
                    "id": "department.apparatus",
                    "label": "Apparatus",
                    "fields": [
                        {"path": "department.apparatus[].unit_id", "label": "Unit ID", "type": "string", "required": True},
                        {"path": "department.apparatus[].unit_type_code", "label": "Unit Type", "type": "string", "required": True, "value_set": "UNIT_TYPE"},
                    ],
                },
            ],
            "value_sets": {k: {"allowed": [i["code"] for i in v.get("items", [])]} for k, v in value_sets.items()},
            "constraints": [],
        }

    def _build_incident_rules(self, raw_files: dict[str, bytes], value_sets: dict[str, Any]) -> dict[str, Any]:
        sections = _parse_incident_modules(raw_files, value_sets)
        if not sections:
            sections = _wi_default_incident_sections()

        return {
            "entity_type": "INCIDENT",
            "sections": sections,
            "value_sets": {k: {"allowed": [i["code"] for i in v.get("items", [])]} for k, v in value_sets.items()},
            "constraints": [
                {
                    "id": "incident.end_after_start",
                    "type": "compare",
                    "a": "incident.end_datetime",
                    "op": ">=",
                    "b": "incident.start_datetime",
                    "severity": "warning",
                    "message": "Incident end time should be after start time.",
                },
                {
                    "id": "incident.type_required",
                    "type": "required",
                    "path": "incident.type_code",
                    "severity": "error",
                    "message": "Incident type is required.",
                },
            ],
        }


def _parse_incident_modules(raw_files: dict[str, bytes], value_sets: dict[str, Any]) -> list[dict]:
    sections = []
    for path, content in raw_files.items():
        path_lower = path.lower()
        if "incident" in path_lower and path_lower.endswith((".yml", ".yaml")):
            try:
                parsed = yaml.safe_load(content.decode("utf-8", errors="replace")) or {}
                if isinstance(parsed, dict) and "fields" in parsed:
                    sec_id = parsed.get("id") or parsed.get("code") or "incident"
                    sec_label = parsed.get("label") or parsed.get("name") or "Incident"
                    fields = []
                    for f in parsed.get("fields", []):
                        if isinstance(f, dict):
                            fields.append({
                                "path": f"incident.{f.get('name', f.get('id', ''))}",
                                "label": f.get("label") or f.get("name") or "",
                                "type": f.get("type") or "string",
                                "required": bool(f.get("required", False)),
                                **({"value_set": f["valueSet"].upper()} if f.get("valueSet") else {}),
                            })
                    if fields:
                        sections.append({"id": sec_id, "label": sec_label, "fields": fields})
            except Exception:
                pass
    return sections


def _wi_default_value_sets() -> dict[str, Any]:
    return {
        "INCIDENT_TYPE": {
            "name": "Incident Type",
            "source_path": "defaults/wi",
            "items": [
                {"code": "100", "display": "Fire"},
                {"code": "111", "display": "Building fire"},
                {"code": "120", "display": "Fire in mobile property"},
                {"code": "200", "display": "Overpressure rupture"},
                {"code": "300", "display": "Rescue & EMS"},
                {"code": "311", "display": "Medical assist, assist EMS crew"},
                {"code": "320", "display": "Emergency medical service"},
                {"code": "400", "display": "Hazardous condition"},
                {"code": "500", "display": "Service call"},
                {"code": "600", "display": "Good intent call"},
                {"code": "700", "display": "False alarm"},
                {"code": "800", "display": "Severe weather"},
                {"code": "900", "display": "Special incident type"},
                {"code": "UNK", "display": "Unknown"},
            ],
        },
        "UNIT_TYPE": {
            "name": "Unit Type",
            "source_path": "defaults/wi",
            "items": [
                {"code": "ENGINE", "display": "Engine"},
                {"code": "LADDER", "display": "Ladder / Aerial"},
                {"code": "RESCUE", "display": "Rescue"},
                {"code": "TANKER", "display": "Tanker / Tender"},
                {"code": "BRUSH", "display": "Brush / Wildland"},
                {"code": "COMMAND", "display": "Command Vehicle"},
                {"code": "UTILITY", "display": "Utility / Support"},
                {"code": "AMBULANCE", "display": "Ambulance"},
                {"code": "HAZMAT", "display": "HazMat"},
                {"code": "OTHER", "display": "Other"},
            ],
        },
        "ACTION_TAKEN": {
            "name": "Action Taken",
            "source_path": "defaults/wi",
            "items": [
                {"code": "10", "display": "Extinguishment"},
                {"code": "12", "display": "Salvage & overhaul"},
                {"code": "21", "display": "Fire investigation"},
                {"code": "32", "display": "Search & rescue"},
                {"code": "41", "display": "HazMat mitigation"},
                {"code": "51", "display": "Provide first aid"},
                {"code": "52", "display": "Patient assessment"},
                {"code": "71", "display": "Scene safety & control"},
                {"code": "86", "display": "Mutual aid given"},
                {"code": "93", "display": "Cancelled en route"},
            ],
        },
        "PROPERTY_USE": {
            "name": "Property Use",
            "source_path": "defaults/wi",
            "items": [
                {"code": "100", "display": "Assembly"},
                {"code": "200", "display": "Education"},
                {"code": "300", "display": "Health care & detention"},
                {"code": "400", "display": "Residential"},
                {"code": "419", "display": "1 or 2 family dwelling"},
                {"code": "429", "display": "Multi-family dwelling"},
                {"code": "500", "display": "Mercantile & business"},
                {"code": "600", "display": "Industrial"},
                {"code": "700", "display": "Storage"},
                {"code": "800", "display": "Special property"},
                {"code": "900", "display": "Outside or special"},
                {"code": "NNN", "display": "None/Not applicable"},
            ],
        },
        "REPORTING_MODE": {
            "name": "Reporting Mode",
            "source_path": "defaults/wi",
            "items": [
                {"code": "RMS", "display": "RMS (Record Management System)"},
            ],
        },
    }


def _wi_default_incident_sections() -> list[dict]:
    return [
        {
            "id": "incident.basics",
            "label": "Incident Basics",
            "fields": [
                {"path": "incident.incident_number", "label": "Incident Number", "type": "string", "required": True},
                {"path": "incident.start_datetime", "label": "Incident Start Date/Time", "type": "datetime", "required": True},
                {"path": "incident.end_datetime", "label": "Incident End Date/Time", "type": "datetime", "required": False},
                {"path": "incident.type_code", "label": "Incident Type", "type": "string", "required": True, "value_set": "INCIDENT_TYPE"},
                {"path": "incident.location.address", "label": "Incident Address", "type": "string", "required": True},
                {"path": "incident.location.city", "label": "City", "type": "string", "required": True},
                {"path": "incident.location.state", "label": "State", "type": "string", "required": True},
                {"path": "incident.location.zip", "label": "ZIP Code", "type": "string", "required": False},
            ],
        },
        {
            "id": "incident.property",
            "label": "Property Information",
            "fields": [
                {"path": "incident.property_use_code", "label": "Property Use", "type": "string", "required": False, "value_set": "PROPERTY_USE"},
                {"path": "incident.on_site_materials", "label": "On-Site Materials", "type": "string", "required": False},
            ],
        },
        {
            "id": "incident.units",
            "label": "Units & Personnel",
            "fields": [
                {"path": "incident.units[].unit_id", "label": "Unit ID", "type": "string", "required": True},
                {"path": "incident.units[].arrival_datetime", "label": "Arrival Time", "type": "datetime", "required": False},
                {"path": "incident.units[].departure_datetime", "label": "Departure Time", "type": "datetime", "required": False},
            ],
        },
        {
            "id": "incident.actions",
            "label": "Actions Taken",
            "fields": [
                {"path": "incident.actions[].action_code", "label": "Action Code", "type": "string", "required": False, "value_set": "ACTION_TAKEN"},
                {"path": "incident.actions[].action_datetime", "label": "Action Time", "type": "datetime", "required": False},
            ],
        },
        {
            "id": "incident.outcomes",
            "label": "Outcomes",
            "fields": [
                {"path": "incident.outcomes.civilian_injuries", "label": "Civilian Injuries", "type": "integer", "required": False},
                {"path": "incident.outcomes.civilian_fatalities", "label": "Civilian Fatalities", "type": "integer", "required": False},
                {"path": "incident.outcomes.firefighter_injuries", "label": "Firefighter Injuries", "type": "integer", "required": False},
                {"path": "incident.outcomes.firefighter_fatalities", "label": "Firefighter Fatalities", "type": "integer", "required": False},
                {"path": "incident.outcomes.property_loss_estimate", "label": "Property Loss ($)", "type": "number", "required": False},
                {"path": "incident.outcomes.contents_loss_estimate", "label": "Contents Loss ($)", "type": "number", "required": False},
            ],
        },
    ]
