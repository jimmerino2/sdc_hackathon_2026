from fastapi import APIRouter, Depends, HTTPException

from app.auth import service
from app.auth.deps import get_current_user
from app.auth.schemas import Credentials, RegisterOut, SessionOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut, status_code=201)
def register(body: Credentials):
    """Create an account. If email confirmation is on in Supabase, `session` is null until the email is confirmed."""
    try:
        return service.register(body)
    except service.AuthFailure as e:
        raise HTTPException(e.status_code, e.message)


@router.post("/login", response_model=SessionOut)
def login(body: Credentials):
    """Log in with email and password; returns the tokens to send as `Authorization: Bearer <access_token>`."""
    try:
        return service.login(body)
    except service.AuthFailure as e:
        raise HTTPException(e.status_code, e.message)


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    """The logged-in user for the bearer token."""
    return user
