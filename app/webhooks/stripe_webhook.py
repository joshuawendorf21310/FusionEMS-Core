from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.json()
    return {"received": True, "event_type": payload.get("type")}