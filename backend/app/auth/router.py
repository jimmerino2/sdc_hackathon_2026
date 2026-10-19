from fastapi import APIRouter, Depends
from supabase import Client

from app.auth import service
from app.auth.schemas import Credentials, TokenOut, UserOut
from app.deps import get_current_user, get_supabase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
def signup(data: Credentials, supabase: Client = Depends(get_supabase)):
    return service.sign_up(supabase, data)


@router.post("/login", response_model=TokenOut)
def login(data: Credentials, supabase: Client = Depends(get_supabase)):
    return service.sign_in(supabase, data)


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email)
