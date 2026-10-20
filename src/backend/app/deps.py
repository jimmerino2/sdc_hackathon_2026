from supabase import Client

from app.supabase import get_client


def get_supabase() -> Client:
    return get_client()
