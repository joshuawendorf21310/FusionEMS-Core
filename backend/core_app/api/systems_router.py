from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/systems", tags=["systems"])

class SystemRow(BaseModel):
    system_key: str
    name: str
    description: str
    status: str
    accent: str

# DB-backed registry is the target; until seeded, we provide deterministic defaults.
SYSTEMS = [
    SystemRow(system_key="fusionbilling", name="FusionBilling", description="Revenue & claims engine", status="ACTIVE", accent="#22d3ee"),
    SystemRow(system_key="fusionems", name="FusionEMS", description="Clinical documentation engine", status="CERTIFICATION_ACTIVATION_REQUIRED", accent="#fb923c"),
    SystemRow(system_key="fusionfire", name="FusionFire", description="Fire reporting engine", status="CERTIFICATION_ACTIVATION_REQUIRED", accent="#ef4444"),
    SystemRow(system_key="fusionhems", name="FusionHEMS", description="Air medical operations engine", status="ARCHITECTURE_COMPLETE", accent="#f59e0b"),
    SystemRow(system_key="fusioncompliance", name="FusionCompliance", description="Compliance & audit layer", status="ACTIVE_CORE_LAYER", accent="#a855f7"),
    SystemRow(system_key="fusionai", name="FusionAI", description="Governed AI co-pilot layer", status="ACTIVE_CORE_LAYER", accent="#ffffff"),
    SystemRow(system_key="fusionfleet", name="FusionFleet", description="Fleet readiness engine", status="IN_DEVELOPMENT", accent="#3b82f6"),
    SystemRow(system_key="fusioncad", name="FusionCAD", description="Computer-Aided Dispatch & Incident Coordination Engine", status="INFRASTRUCTURE_LAYER", accent="#94a3b8"),
]

@router.get("", response_model=list[SystemRow])
def list_systems():
    return SYSTEMS
