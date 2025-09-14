# backend/routes/scraper.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import List

from ..services import database, scraper as scraper_service
from ..models.product import Product as ProductModel
from ..routes.products import Product as ProductSchema # Reutilizar el esquema Pydantic

router = APIRouter(
    prefix="/scrape",
    tags=["Scraper"],
)

class ScrapeRequest(BaseModel):
    url: HttpUrl

@router.post("/", response_model=ProductSchema)
async def scrape_product(request: ScrapeRequest, db: Session = Depends(database.get_db)):
    """
    Activa el scraper para una URL de producto específica y guarda/actualiza los datos en la base de datos.
    """
    try:
        product = await scraper_service.scrape_product_data(str(request.url), db)
        return product
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud de scraping: {e}")
