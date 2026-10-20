from app.product.schemas import ProductCreate


def list_products() -> list[dict]:
    # PLACEHOLDER: replace with a Supabase query, e.g.
    # supabase.table("products").select("*").execute().data
    return []


def create_product(data: ProductCreate) -> dict:
    # PLACEHOLDER: replace with a Supabase insert, e.g.
    # supabase.table("products").insert(data.model_dump()).execute().data[0]
    return {"id": 0, **data.model_dump()}
