from fastapi import FastAPI
from app.api.router import api_router
from app.metrics.routes import router as metrics_router
from app.webhooks.stripe_webhook import router as webhook_router
from app.middleware.error_handler import global_exception_handler
from app.tenancy.middleware import tenant_middleware
from app.core.structured_logging import setup_json_logging

setup_json_logging()

app = FastAPI(title="FusionEMS Quantum", version="1.0.0")

app.middleware("http")(global_exception_handler)
app.middleware("http")(tenant_middleware)

@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(api_router, prefix="/api")
app.include_router(metrics_router)
app.include_router(webhook_router, prefix="/webhooks")