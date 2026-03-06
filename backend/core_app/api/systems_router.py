from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/systems", tags=["Systems"])

_SYSTEMS = [
    {
        "system_key": "fusionbilling",
        "name": "FusionBilling",
        "description": "Revenue & claims engine",
        "status": "ACTIVE",
        "accent": "#22d3ee",
    },
    {
        "system_key": "fusionems",
        "name": "FusionEMS",
        "description": "Clinical documentation engine",
        "status": "CERTIFICATION_ACTIVATION_REQUIRED",
        "accent": "#f97316",
    },
    {
        "system_key": "fusionfire",
        "name": "FusionFire",
        "description": "Fire reporting engine",
        "status": "CERTIFICATION_ACTIVATION_REQUIRED",
        "accent": "#ef4444",
    },
    {
        "system_key": "fusionhems",
        "name": "FusionHEMS",
        "description": "Air medical operations engine",
        "status": "ARCHITECTURE_COMPLETE",
        "accent": "#f59e0b",
    },
    {
        "system_key": "fusioncompliance",
        "name": "FusionCompliance",
        "description": "Compliance & audit layer",
        "status": "ACTIVE_CORE_LAYER",
        "accent": "#8b5cf6",
    },
    {
        "system_key": "fusionai",
        "name": "FusionAI",
        "description": "Governed AI co-pilot layer",
        "status": "ACTIVE_CORE_LAYER",
        "accent": "#10b981",
    },
    {
        "system_key": "fusionfleet",
        "name": "FusionFleet",
        "description": "Fleet readiness engine",
        "status": "ACTIVE_CORE_LAYER",
        "accent": "#0ea5e9",
    },
    {
        "system_key": "fusioncad",
        "name": "FusionCAD",
        "description": "CAD & incident coordination engine",
        "status": "INFRASTRUCTURE_LAYER",
        "accent": "#6366f1",
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
