from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.roi.engine import compute_roi, hash_outputs
from core_app.schemas.roi import RoiInput, RoiScenarioResponse

router = APIRouter(prefix="/public/roi", tags=["roi"])

@router.post("/calc", response_model=RoiScenarioResponse)
def calc(payload: RoiInput, db: Session = Depends(db_session_dependency)) -> RoiScenarioResponse:
    outputs = compute_roi(payload.model_dump())
    outputs_hash = hash_outputs(outputs)
    row = db.execute(
        text("""
            INSERT INTO roi_scenarios (zip_code, inputs, outputs, outputs_hash)
            VALUES (:zip, :inputs::jsonb, :outputs::jsonb, :h)
            RETURNING id
        """),
        {
            "zip": payload.zip_code,
            "inputs": json.dumps(payload.model_dump()),
            "outputs": json.dumps(outputs),
            "h": outputs_hash,
        },
    ).mappings().first()
    db.commit()
    return RoiScenarioResponse(id=str(row["id"]), outputs=outputs, outputs_hash=outputs_hash)


@router.post("/proposal-pdf")
def proposal_pdf(payload: RoiInput, db: Session = Depends(db_session_dependency)) -> Response:
    """Generate a PDF ROI proposal for the given ROI inputs."""
    from core_app.builders.pdf_generator import generate_roi_proposal_pdf

    outputs = compute_roi(payload.model_dump())
    agency_info = {
        "name": getattr(payload, "agency_name", None) or "Your Agency",
        "zip_code": payload.zip_code,
    }
    pdf_bytes = generate_roi_proposal_pdf(roi_data=outputs, agency_info=agency_info)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fusionems-roi-proposal.pdf"},
    )
