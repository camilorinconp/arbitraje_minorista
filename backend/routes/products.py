# backend/routes/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from ..services import database
from ..models import product as product_model

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)

# Pydantic schema for displaying a product
class Product(BaseModel):
    id: int
    name: str
    price: float
    product_url: str
    image_url: str | None = None
    last_scraped_at: datetime

    class Config:
        orm_mode = True

@router.get("/", response_model=List[Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Obtiene una lista de productos de la base de datos.
    """
    products = db.query(product_model.Product).offset(skip).limit(limit).all()
    return products
