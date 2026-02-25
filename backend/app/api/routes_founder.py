from fastapi import APIRouter

router = APIRouter()

@router.get("/executive-summary")
def executive_summary():
    return {
        "mrr": 0,
        "clients": 0,
        "system": "operational"
    }