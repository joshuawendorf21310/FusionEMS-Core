from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class SyncConflictPolicy(StrEnum):
    FIELD_WINS = "field_wins"
    STATION_WINS = "station_wins"
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"


class SyncEngine:
    def resolve_conflict(
        self,
        field_chart: dict[str, Any],
        station_chart: dict[str, Any],
        policy: SyncConflictPolicy = SyncConflictPolicy.LAST_WRITE_WINS,
    ) -> tuple[dict[str, Any], list[str]]:
        notes: list[str] = []
        if policy == SyncConflictPolicy.FIELD_WINS:
            resolved = dict(field_chart)
            notes.append("Field version wins: all field edits applied")
        elif policy == SyncConflictPolicy.STATION_WINS:
            resolved = dict(station_chart)
            notes.append("Station version wins: all station edits applied")
        elif policy == SyncConflictPolicy.LAST_WRITE_WINS:
            field_ts = field_chart.get("updated_at", "")
            station_ts = station_chart.get("updated_at", "")
            if field_ts >= station_ts:
                resolved = dict(field_chart)
                notes.append(f"Field version wins by timestamp: {field_ts} >= {station_ts}")
            else:
                resolved = dict(station_chart)
                notes.append(f"Station version wins by timestamp: {station_ts} > {field_ts}")
        else:
            resolved = dict(station_chart)
            field_safe = ["vitals", "medications", "procedures", "assessments", "attachments"]
            for key in field_safe:
                if key in field_chart and field_chart[key]:
                    existing_ids = {
                        item.get("vital_id")
                        or item.get("med_id")
                        or item.get("proc_id")
                        or item.get("assessment_id")
                        for item in resolved.get(key, [])
                        if isinstance(item, dict)
                    }
                    for item in field_chart[key]:
                        item_id = (
                            item.get("vital_id")
                            or item.get("med_id")
                            or item.get("proc_id")
                            or item.get("assessment_id")
                        )
                        if item_id not in existing_ids:
                            resolved.setdefault(key, []).append(item)
                            notes.append(f"Merged field item {item_id} into {key}")
        field_log = field_chart.get("_event_log", [])
        station_log = station_chart.get("_event_log", [])
        merged_log_map = {e.get("event_id"): e for e in station_log}
        for e in field_log:
            merged_log_map[e.get("event_id")] = e
        resolved["_event_log"] = sorted(
            merged_log_map.values(), key=lambda x: x.get("timestamp", "")
        )
        resolved["sync_status"] = "synced"
        resolved["updated_at"] = datetime.now(UTC).isoformat()
        return resolved, notes

    def build_sync_delta(
        self, local_chart: dict[str, Any], server_chart: dict[str, Any]
    ) -> dict[str, Any]:
        delta: dict[str, Any] = {}
        skip = {"_event_log", "updated_at", "sync_status"}
        for key in set(list(local_chart.keys()) + list(server_chart.keys())):
            if key in skip:
                continue
            local_val = local_chart.get(key)
            server_val = server_chart.get(key)
            if local_val != server_val:
                delta[key] = {"local": local_val, "server": server_val}
        return delta

    def apply_delta(self, base_chart: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
        result = dict(base_chart)
        for key, change in delta.items():
            result[key] = change.get("local", change.get("server"))
        result["updated_at"] = datetime.now(UTC).isoformat()
        return result

    def compute_sync_hash(self, chart: dict[str, Any]) -> str:
        exclude = {
            "updated_at",
            "sync_status",
            "_event_log",
            "completeness_score",
            "completeness_issues",
        }
        clean = {k: v for k, v in chart.items() if k not in exclude}
        serialized = json.dumps(clean, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def create_event_log_entry(
        self,
        chart_id: str,
        action: str,
        actor: str,
        field_changes: dict[str, Any],
    ) -> dict[str, Any]:
        entry = {
            "event_id": str(uuid.uuid4()),
            "chart_id": chart_id,
            "action": action,
            "actor": actor,
            "timestamp": datetime.now(UTC).isoformat(),
            "field_changes": field_changes,
        }
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True, default=str).encode()
        ).hexdigest()
        return entry
