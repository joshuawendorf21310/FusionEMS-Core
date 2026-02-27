from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core_app.api.dependencies import get_current_user
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/systems", tags=["Systems"])

_SYSTEMS = [
    {
        "system_key": "fusioncad",
        "name": "FusionCAD",
        "description": "Computer-Aided Dispatch — multi-agency quantum infrastructure layer.",
        "status": "PENDING",
        "accent": "#6366f1",
    },
    {
        "system_key": "fusionbilling",
        "name": "FusionBilling",
        "description": "Integrated 837/835 EDI billing, AR management, and revenue cycle automation.",
        "status": "ACTIVE",
        "accent": "#22d3ee",
    },
    {
        "system_key": "fusionhems",
        "name": "FusionHEMS",
        "description": "Helicopter EMS dispatch, pilot portal, mission lifecycle, and flight billing.",
        "status": "ACTIVE",
        "accent": "#f59e0b",
    },
    {
        "system_key": "fusionepcr",
        "name": "FusionePCR",
        "description": "NEMSIS 3.5.1-compliant ePCR capture, validation, and state submission.",
        "status": "ACTIVE",
        "accent": "#10b981",
    },
    {
        "system_key": "fusionneris",
        "name": "FusionNERIS",
        "description": "Fire incident reporting and NERIS compliance studio.",
        "status": "ACTIVE",
        "accent": "#ef4444",
    },
    {
        "system_key": "fusiontrack",
        "name": "FusionTrack",
        "description": "Asset and unit tracking with real-time GPS and crew location.",
        "status": "ACTIVE",
        "accent": "#8b5cf6",
    },
    {
        "system_key": "fusionmdt",
        "name": "FusionMDT",
        "description": "Mobile Data Terminal with offline ePCR, vitals, and medication logging.",
        "status": "ACTIVE",
        "accent": "#06b6d4",
    },
    {
        "system_key": "fusionkitlink",
        "name": "FusionKitLink",
        "description": "Medication kit and controlled-substance compliance tracking.",
        "status": "ACTIVE",
        "accent": "#84cc16",
    },
    {
        "system_key": "fusionfhir",
        "name": "FusionFHIR",
        "description": "HL7 FHIR R4 bridge for hospital integration and care continuity.",
        "status": "PENDING",
        "accent": "#94a3b8",
    },
]


@router.get("")
async def list_systems(
    current: CurrentUser = Depends(get_current_user),
):
    return _SYSTEMS


@router.get("/{system_key}")
async def get_system(
    system_key: str,
    current: CurrentUser = Depends(get_current_user),
):
    for s in _SYSTEMS:
        if s["system_key"] == system_key:
            return s
    raise HTTPException(status_code=404, detail="system_not_found")
