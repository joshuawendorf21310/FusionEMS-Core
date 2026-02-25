from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.roi.engine import compute_roi, hash_outputs
from core_app.schemas.onboarding import OnboardingStartRequest, OnboardingStartResponse

router = APIRouter(prefix="/public/signup", tags=["onboarding"])

@router.post("/start", response_model=OnboardingStartResponse)
def start(payload: OnboardingStartRequest, db: Session = Depends(db_session_dependency)) -> OnboardingStartResponse:
    roi = compute_roi({
        "zip_code": payload.zip_code,
        "annual_call_volume": payload.annual_call_volume,
        "service_type": payload.agency_type,
        "current_billing_percent": payload.current_billing_percent,
        "payer_mix": payload.payer_mix,
        "level_mix": payload.level_mix,
        "selected_modules": payload.selected_modules,
    })
    roi_hash = hash_outputs(roi)
    row = db.execute(
        text("""
            INSERT INTO onboarding_applications
            (email, agency_name, zip_code, agency_type, annual_call_volume, current_billing_percent,
             payer_mix, level_mix, selected_modules, roi_snapshot_hash, status)
            VALUES
            (:email, :agency, :zip, :atype, :vol, :pct, :payer::jsonb, :level::jsonb, :mods::jsonb, :h, 'started')
            RETURNING id
        """),
        {
            "email": payload.email.lower(),
            "agency": payload.agency_name,
            "zip": payload.zip_code,
            "atype": payload.agency_type,
            "vol": payload.annual_call_volume,
            "pct": payload.current_billing_percent,
            "payer": json.dumps(payload.payer_mix),
            "level": json.dumps(payload.level_mix),
            "mods": json.dumps(payload.selected_modules),
            "h": roi_hash,
        },
    ).mappings().first()
    db.commit()
    return OnboardingStartResponse(application_id=str(row["id"]), roi_snapshot_hash=roi_hash, status="started")
