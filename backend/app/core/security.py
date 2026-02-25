import requests
from jose import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_settings

security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    settings = get_settings()
    token = credentials.credentials
    jwks_url = f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    jwks = requests.get(jwks_url).json()

    headers = jwt.get_unverified_header(token)
    key = next((k for k in jwks["keys"] if k["kid"] == headers["kid"]), None)

    if not key:
        raise HTTPException(status_code=401, detail="Invalid token")

    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=settings.COGNITO_CLIENT_ID
    )