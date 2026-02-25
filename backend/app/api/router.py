from fastapi import APIRouter
from app.api.routes_founder import router as founder_router

api_router = APIRouter()
api_router.include_router(founder_router, prefix="/founder")