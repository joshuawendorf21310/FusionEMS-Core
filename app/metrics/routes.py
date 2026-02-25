from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
def metrics():
    return {"status": "metrics endpoint ready"}