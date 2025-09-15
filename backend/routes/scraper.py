# backend/routes/scraper.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from ..services import database, scraper as scraper_service
from .gestion_datos import Producto  # Reutilizamos el schema de Producto

router = APIRouter(
    prefix="/scraper",
    tags=["Scraper"],
)


class ScrapeRequest(BaseModel):
    product_url: HttpUrl
    id_minorista: int


@router.post("/run/", response_model=Producto)
async def activar_scraper(
    request: ScrapeRequest, db: Session = Depends(database.get_db)
):
    """
    Activa el scraper para una URL de producto específica de un minorista y guarda/actualiza los datos.
    """
    try:
        producto = await scraper_service.scrape_product_data(
            str(request.product_url), request.id_minorista, db
        )
        return producto
    except HTTPException as e:
        # Re-lanzar excepciones HTTP ya manejadas (ej. 404 de minorista no encontrado)
        raise e
    except Exception as e:
        # Capturar cualquier otra excepción inesperada
        raise HTTPException(
            status_code=500, detail=f"Error al procesar la solicitud de scraping: {e}"
        )
