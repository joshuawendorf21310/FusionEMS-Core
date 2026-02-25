from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/status")
def status() -> dict:
    # Minimal operational status envelope
    return {
        "system_status": "operational",
        "billing_engine": "active",
        "compliance_layer": "monitoring",
        "version": "quantum-v1"
    }
