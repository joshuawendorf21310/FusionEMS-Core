from fastapi import FastAPI
from app.api.router import api_router
from app.middleware.tenant_middleware import tenant_middleware
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="FusionEMS Quantum", version="FINAL")

app.middleware("http")(tenant_middleware)

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(api_router, prefix="/api")