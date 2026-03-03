from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


NERIS_ENTITY_SCHEMA_VERSION = "1.0"
NERIS_INCIDENT_SCHEMA_VERSION = "1.0"


@dataclass
class NERISFieldMapping:
    source_field: str
    target_field: str
    transform: Optional[str] = None
    required: bool = False


ENTITY_MAPPINGS: list[NERISFieldMapping] = [
    NERISFieldMapping("department_name", "entity.name", required=True),
    NERISFieldMapping("department_id", "entity.identifier", required=True),
    NERISFieldMapping("state_code", "entity.state", required=True),
    NERISFieldMapping("county", "entity.county"),
    NERISFieldMapping("fdid", "entity.fdid", required=True),
    NERISFieldMapping("station_count", "entity.stations"),
    NERISFieldMapping("apparatus_count", "entity.apparatus"),
    NERISFieldMapping("personnel_count", "entity.personnel"),
    NERISFieldMapping("nfpa_region", "entity.nfpa_region"),
    NERISFieldMapping("organization_type", "entity.org_type"),
]

INCIDENT_MAPPINGS: list[NERISFieldMapping] = [
    NERISFieldMapping("incident_id", "incident.identifier", required=True),
    NERISFieldMapping("incident_date", "incident.alarm_datetime", required=True),
    NERISFieldMapping("incident_type_code", "incident.type_code", required=True),
    NERISFieldMapping("incident_type_desc", "incident.type_description"),
    NERISFieldMapping("location.address", "incident.address"),
    NERISFieldMapping("location.city", "incident.city"),
    NERISFieldMapping("location.state", "incident.state"),
    NERISFieldMapping("location.zip", "incident.zip"),
    NERISFieldMapping("location.latitude", "incident.geo.lat"),
    NERISFieldMapping("location.longitude", "incident.geo.lon"),
    NERISFieldMapping("property_use_code", "incident.property_use"),
    NERISFieldMapping("mutual_aid", "incident.mutual_aid"),
    NERISFieldMapping("shift", "incident.shift"),
    NERISFieldMapping("actions_taken", "incident.actions", transform="array"),
    NERISFieldMapping("units", "incident.units", transform="array"),
    NERISFieldMapping("casualties.civilian_deaths", "incident.casualties.civilian_deaths"),
    NERISFieldMapping("casualties.civilian_injuries", "incident.casualties.civilian_injuries"),
    NERISFieldMapping("casualties.ff_deaths", "incident.casualties.firefighter_deaths"),
    NERISFieldMapping("casualties.ff_injuries", "incident.casualties.firefighter_injuries"),
    NERISFieldMapping("property_loss", "incident.property_loss"),
    NERISFieldMapping("contents_loss", "incident.contents_loss"),
    NERISFieldMapping("dispatch_time", "incident.times.dispatch"),
    NERISFieldMapping("arrival_time", "incident.times.arrival"),
    NERISFieldMapping("controlled_time", "incident.times.controlled"),
    NERISFieldMapping("cleared_time", "incident.times.cleared"),
]


@dataclass
class MappingResult:
    success: bool
    mapped_data: dict = field(default_factory=dict)
    unmapped_fields: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "mapped_data": self.mapped_data,
            "unmapped_fields": self.unmapped_fields,
            "errors": self.errors,
        }


class NERISSchemaAdapter:
    def __init__(self):
        self._entity_mappings = ENTITY_MAPPINGS
        self._incident_mappings = INCIDENT_MAPPINGS

    def map_entity(self, source: dict) -> MappingResult:
        return self._apply_mappings(source, self._entity_mappings, "entity")

    def map_incident(self, source: dict) -> MappingResult:
        return self._apply_mappings(source, self._incident_mappings, "incident")

    def _apply_mappings(
        self, source: dict, mappings: list[NERISFieldMapping], schema_type: str
    ) -> MappingResult:
        result = MappingResult(success=True)
        result.mapped_data["_schema_version"] = (
            NERIS_ENTITY_SCHEMA_VERSION if schema_type == "entity" else NERIS_INCIDENT_SCHEMA_VERSION
        )
        result.mapped_data["_schema_type"] = schema_type

        for mapping in mappings:
            value = self._resolve_source(source, mapping.source_field)
            if value is None:
                if mapping.required:
                    result.errors.append(f"Required field missing: {mapping.source_field}")
                    result.success = False
                else:
                    result.unmapped_fields.append(mapping.source_field)
                continue

            if mapping.transform == "array" and not isinstance(value, list):
                value = [value]

            self._set_nested(result.mapped_data, mapping.target_field, value)

        return result

    @staticmethod
    def _resolve_source(source: dict, path: str) -> Any:
        parts = path.split(".")
        current = source
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    @staticmethod
    def _set_nested(target: dict, path: str, value: Any) -> None:
        parts = path.split(".")
        current = target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
