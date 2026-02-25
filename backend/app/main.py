from fastapi import FastAPI
from app.api.router import api_router
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="FusionEMS Quantum", version="3.0.0")

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(api_router, prefix="/api")