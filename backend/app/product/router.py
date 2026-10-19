from fastapi import APIRouter, Depends
from supabase import Client

from app.deps import get_current_user, get_supabase
from app.product import service
from app.product.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/product", tags=["product"])


@router.get("", response_model=list[ProductOut])
def list_products(supabase: Client = Depends(get_supabase)):
    return service.list_products(supabase)


@router.post("", response_model=ProductOut)
def create_product(
    data: ProductCreate,
    supabase: Client = Depends(get_supabase),
    user=Depends(get_current_user),
):
    return service.create_product(supabase, data)
