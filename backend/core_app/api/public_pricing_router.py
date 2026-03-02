from __future__ import annotations

from fastapi import APIRouter

from core_app.pricing.catalog import get_catalog

router = APIRouter(prefix="/public/pricing", tags=["Pricing Catalog"])


@router.get("/catalog")
async def pricing_catalog() -> dict:
    return get_catalog()
