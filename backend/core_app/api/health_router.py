from datetime import datetime
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/api/v1/health")
def api_health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}

@router.get("/api/v1/status")
def status():
    return {
        "systemStatus": "Operational",
        "billingEngine": "Active",
        "complianceLayer": "Monitoring",
        "version": "Quantum v1.0",
        "time": datetime.utcnow().isoformat() + "Z",
    }
