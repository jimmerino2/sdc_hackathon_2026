from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.supabase import get_client

bearer = HTTPBearer()


def get_supabase() -> Client:
    return get_client()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    supabase: Client = Depends(get_supabase),
):
    """Verify the Supabase JWT sent by the frontend and return the user."""
    try:
        res = supabase.auth.get_user(creds.credentials)
        if res is None or res.user is None:
            raise ValueError("no user")
        return res.user
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
