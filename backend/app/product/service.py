from supabase import Client

from app.product.schemas import ProductCreate

TABLE = "products"


def list_products(supabase: Client) -> list[dict]:
    return supabase.table(TABLE).select("*").execute().data


def create_product(supabase: Client, data: ProductCreate) -> dict:
    return supabase.table(TABLE).insert(data.model_dump()).execute().data[0]
