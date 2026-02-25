from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token=Depends(security)):
    return {"sub": "placeholder-user"}