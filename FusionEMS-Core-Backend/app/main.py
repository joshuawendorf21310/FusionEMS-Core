from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="FusionEMS Quantum", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(api_router, prefix="/api")