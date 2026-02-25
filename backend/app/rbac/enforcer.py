from fastapi import HTTPException

ROLE_PERMISSIONS = {
    "founder": ["*"],
    "admin": ["read", "write"],
    "user": ["read"]
}

def enforce(role: str, action: str):
    permissions = ROLE_PERMISSIONS.get(role, [])
    if "*" in permissions or action in permissions:
        return True
    raise HTTPException(status_code=403, detail="Permission denied")