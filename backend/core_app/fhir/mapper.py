from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from core_app.models.patient import Patient
from core_app.models.incident import Incident


def _fhir_id(u: UUID | str) -> str:
    return str(u)


def map_patient(p: Patient) -> dict:
    name = {"family": p.last_name, "given": [p.first_name] + ([p.middle_name] if p.middle_name else [])}
    gender_map = {
        "female": "female",
        "male": "male",
        "non_binary": "other",
        "other": "other",
        "unknown": "unknown",
    }
    return {
        "resourceType": "Patient",
        "id": _fhir_id(p.id),
        "identifier": [{"system": "urn:fusionems:patient", "value": p.external_identifier}] if p.external_identifier else [],
        "name": [name],
        "gender": gender_map.get(p.gender.value, "unknown"),
        "birthDate": p.date_of_birth.isoformat() if p.date_of_birth else None,
    }


def map_incident_to_encounter(i: Incident) -> dict:
    period = {}
    if i.dispatch_time:
        period["start"] = i.dispatch_time.isoformat()
    if i.arrival_time:
        period["end"] = i.arrival_time.isoformat()
    return {
        "resourceType": "Encounter",
        "id": _fhir_id(i.id),
        "identifier": [{"system": "urn:fusionems:incident", "value": i.incident_number}],
        "status": "in-progress" if i.status.value in ("draft","in_progress","ready_for_review") else "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "EMER", "display": "emergency"},
        "period": period,
    }


def map_to_fhir(db: Session, tenant_id: UUID, entity_type: str, entity_id: str) -> tuple[str, dict]:
    if entity_type == "patient":
        p = db.scalar(select(Patient).where(Patient.id == UUID(entity_id), Patient.tenant_id == tenant_id, Patient.deleted_at.is_(None)))
        if not p:
            raise ValueError("Patient not found")
        return "Patient", map_patient(p)
    if entity_type in ("incident","call"):
        i = db.scalar(select(Incident).where(Incident.id == UUID(entity_id), Incident.tenant_id == tenant_id, Incident.deleted_at.is_(None)))
        if not i:
            raise ValueError("Incident not found")
        return "Encounter", map_incident_to_encounter(i)
    # Fire report mapping can be added as custom FHIR Composition
    raise ValueError("Unsupported entity type")
