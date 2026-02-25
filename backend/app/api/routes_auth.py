from fastapi import APIRouter

router = APIRouter()

@router.get("/me")
def get_me():
    return {"message": "Auth endpoint working"}