from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.schemas.fhir import FhirExportRequest, FhirExportResponse
from core_app.fhir.mapper import map_to_fhir

router = APIRouter(prefix="/fhir", tags=["fhir"])

@router.post("/export", response_model=FhirExportResponse)
def export_fhir(payload: FhirExportRequest, db: Session = Depends(db_session_dependency), user: CurrentUser = Depends(get_current_user)) -> FhirExportResponse:
    resource_type, resource = map_to_fhir(db, user.tenant_id, payload.entity_type, payload.entity_id)
    row = db.execute(
        text("""
            INSERT INTO fhir_artifacts (tenant_id, entity_type, entity_id, resource_type, resource_json)
            VALUES (:tid, :etype, :eid, :rtype, :r::jsonb)
            RETURNING id
        """),
        {"tid": str(user.tenant_id), "etype": payload.entity_type, "eid": payload.entity_id, "rtype": resource_type, "r": json.dumps(resource)},
    ).mappings().first()
    db.commit()
    return FhirExportResponse(artifact_id=str(row["id"]), resource_type=resource_type, resource=resource)
