from fastapi import Request, HTTPException

async def tenant_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    request.state.tenant_id = tenant_id
    return await call_next(request)