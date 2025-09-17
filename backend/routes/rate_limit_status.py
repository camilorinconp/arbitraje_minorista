# backend/routes/rate_limit_status.py

from fastapi import APIRouter, Request
from typing import Dict, Any

from ..services.rate_limiter import limiter, get_rate_limit_status

router = APIRouter(prefix="/rate-limit", tags=["Rate Limiting"])


@router.get("/status", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_current_rate_limit_status(request: Request):
    """
    Obtener estado actual de rate limiting para el cliente.
    """
    status = await get_rate_limit_status(request)
    return status


@router.get("/limits", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def get_rate_limits_info(request: Request):
    """
    Obtener información sobre los límites de rate limiting configurados.
    """
    return {
        "limits": {
            "scraping": {
                "description": "Endpoints de scraping (más restrictivos)",
                "limits": ["10/minute", "100/hour", "500/day"],
                "endpoints": ["/scraper/run/"]
            },
            "data_management": {
                "description": "Gestión de datos (moderadamente restrictivo)",
                "limits": {
                    "create": ["30/minute", "200/hour"],
                    "update": ["20/minute", "150/hour"],
                    "delete": ["10/minute", "50/hour"],
                    "read": ["100/minute", "1000/hour"]
                },
                "endpoints": ["/gestion-datos/*"]
            },
            "monitoring": {
                "description": "Endpoints de monitoreo",
                "limits": ["100/minute", "2000/hour"],
                "endpoints": ["/monitoring/*"]
            },
            "observability": {
                "description": "Health checks y métricas (muy permisivo)",
                "limits": ["200/minute", "5000/hour"],
                "endpoints": ["/observability/*"]
            }
        },
        "headers": {
            "X-RateLimit-Limit": "Número de requests permitidos en la ventana",
            "X-RateLimit-Remaining": "Requests restantes en la ventana actual",
            "X-RateLimit-Reset": "Tiempo hasta reset de la ventana (segundos)",
            "Retry-After": "Tiempo a esperar antes del próximo request (en caso de exceder límite)"
        },
        "notes": [
            "Los límites se aplican por IP address",
            "En el futuro se implementará rate limiting por usuario autenticado",
            "Para producción se recomienda usar Redis como storage"
        ]
    }