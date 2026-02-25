from fastapi import APIRouter, Depends
from app.core.security import verify_jwt

router = APIRouter()

@router.get("/executive-summary")
def executive_summary(user=Depends(verify_jwt)):
    return {
        "mrr": 0,
        "clients": 0,
        "system_status": "operational",
        "user": user.get("sub")
    }