from fastapi import APIRouter

from app.product import service
from app.product.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/product", tags=["product"])


@router.get("", response_model=list[ProductOut])
def list_products():
    return service.list_products()


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate):
    return service.create_product(data)
