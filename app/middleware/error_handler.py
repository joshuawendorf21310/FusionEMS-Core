from fastapi import Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})