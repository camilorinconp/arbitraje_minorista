# backend/routes/scraper.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from ..services import database, scraper as scraper_service
from ..services.rate_limiter import limiter, SCRAPING_LIMITS
from .gestion_datos import Producto  # Reutilizamos el schema de Producto

# Import authentication dependencies
from ..auth.middleware import get_current_user, require_permission
from ..auth.models import User

router = APIRouter(
    prefix="/scraper",
    tags=["Scraper"],
)


class ScrapeRequest(BaseModel):
    product_url: HttpUrl
    id_minorista: int


@router.post("/run/", response_model=Producto)
@limiter.limit("10/minute")
@limiter.limit("100/hour")
@limiter.limit("500/day")
async def activar_scraper(
    request: Request,
    scrape_request: ScrapeRequest,
    current_user: User = Depends(require_permission("scrape")),
    db: Session = Depends(database.get_db)
):
    """
    Activa el scraper para una URL de producto específica de un minorista y guarda/actualiza los datos.
    """
    try:
        producto = await scraper_service.scrape_product_data(
            str(scrape_request.product_url), scrape_request.id_minorista, db
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
