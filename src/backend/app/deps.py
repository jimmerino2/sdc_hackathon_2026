from fastapi import HTTPException
from supabase import Client

from app.config import get_settings
from app.supabase import get_admin_client, get_client


def get_supabase() -> Client:
    return get_client()


def get_supabase_admin() -> Client:
    if not get_settings().supabase_service_key:
        raise HTTPException(status_code=503, detail="SUPABASE_SERVICE_KEY is not set; this endpoint writes to Supabase")
    return get_admin_client()
