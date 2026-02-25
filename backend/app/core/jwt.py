import requests
from jose import jwt
from fastapi import HTTPException
from app.core.config import settings

JWKS_URL = f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
jwks = requests.get(JWKS_URL).json()

def verify_token(token: str):
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