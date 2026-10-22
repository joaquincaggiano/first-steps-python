from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token, get_current_user
from .schemas import Token, UserPublic


FAKE_USERS = {
    "joaquin@example.com": {
        "email": "joaquin@example.com",
        "username": "joaquin",
        "password": "secret123"
    },
    "alumno@example.com":  {
        "email": "alumno@example.com",
        "username": "alumno",
        "password": "123456"
    },
}

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS.get(form_data.username)

    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Credentials are not valid")

    token = create_access_token(
        data={
            "sub": user["email"],
            "username": user["username"]
        },
        expires_delta=timedelta(minutes=30)
    )

    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: dict = Depends(get_current_user)):
    return UserPublic(**current_user)
