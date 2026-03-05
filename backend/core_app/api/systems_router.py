from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/systems", tags=["Systems"])

_SYSTEMS = [
    {
        "system_key": "fusioncad",
        "name": "FusionCAD",
        "description": "Computer-aided dispatch and incident coordination.",
        "status": "INFRASTRUCTURE_LAYER",
        "accent": "#6366f1",
    },
    {
        "system_key": "fusionbilling",
        "name": "FusionBilling",
        "description": "Integrated billing: 837/835 EDI, AR, and revenue cycle automation.",
        "status": "ACTIVE",
        "accent": "#22d3ee",
    },
    {
        "system_key": "fusionhems",
        "name": "FusionHEMS",
        "description": "Air medical operations: dispatch, mission lifecycle, and flight billing.",
        "status": "ACTIVE",
        "accent": "#f59e0b",
    },
    {
        "system_key": "fusionepcr",
        "name": "FusionePCR",
        "description": "ePCR capture, validation, and NEMSIS submission workflows.",
        "status": "ACTIVE",
        "accent": "#10b981",
    },
    {
        "system_key": "fusionneris",
        "name": "FusionNERIS",
        "description": "Fire incident reporting and NERIS compliance.",
        "status": "ACTIVE",
        "accent": "#ef4444",
    },
    {
        "system_key": "fusiontrack",
        "name": "FusionTrack",
        "description": "Unit and asset tracking with real-time location visibility.",
        "status": "IN_DEVELOPMENT",
        "accent": "#8b5cf6",
    },
    {
        "system_key": "fusionmdt",
        "name": "FusionMDT",
        "description": "Mobile data terminal experiences for field operations.",
        "status": "IN_DEVELOPMENT",
        "accent": "#06b6d4",
    },
    {
        "system_key": "fusionkitlink",
        "name": "FusionKitLink",
        "description": "Medication kits and controlled-substance compliance tracking.",
        "status": "ACTIVE",
        "accent": "#84cc16",
    },
    {
        "system_key": "fusionfhir",
        "name": "FusionFHIR",
        "description": "HL7 FHIR integration bridge for hospital connectivity.",
        "status": "IN_DEVELOPMENT",
        "accent": "#94a3b8",
    },
]


@router.get("")
async def list_systems():
    return _SYSTEMS


@router.get("/{system_key}")
async def get_system(
    system_key: str,
):
    for s in _SYSTEMS:
        if s["system_key"] == system_key:
            return s
    raise HTTPException(status_code=404, detail="system_not_found")
