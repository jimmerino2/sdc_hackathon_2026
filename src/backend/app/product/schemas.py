from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


class ProductOut(ProductCreate):
    id: int
