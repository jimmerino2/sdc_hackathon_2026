from fastapi import HTTPException, status
from supabase import Client

from app.auth.schemas import Credentials, TokenOut, UserOut

def sign_up(supabase: Client, data: Credentials) -> UserOut:
    res = supabase.auth.sign_up({"email": data.email, "password": data.password})
    if res.user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sign up failed")
    return UserOut(id=res.user.id, email=res.user.email)


def sign_in(supabase: Client, data: Credentials) -> TokenOut:
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": data.email, "password": data.password}
        )
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenOut(
        access_token=res.session.access_token,
        user=UserOut(id=res.user.id, email=res.user.email),
    )
