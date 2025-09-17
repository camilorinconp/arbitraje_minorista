# backend/services/rate_limiter.py

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

logger = logging.getLogger(__name__)


def get_client_identifier(request: Request) -> str:
    """
    Obtener identificador único del cliente para rate limiting.
    Usa IP address como identificador base, pero permite extensiones futuras.
    """
    # Priorizar headers de proxy para obtener IP real
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Tomar la primera IP en caso de múltiples proxies
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug(f"Client IP from X-Forwarded-For: {client_ip}")
        return client_ip

    # Fallback a IP remota directa
    client_ip = get_remote_address(request)
    logger.debug(f"Client IP from remote address: {client_ip}")
    return client_ip


def get_authenticated_user_id(request: Request) -> Optional[str]:
    """
    Obtener ID de usuario autenticado para rate limiting por usuario.
    Por ahora retorna None, se puede extender con autenticación real.
    """
    # TODO: Implementar cuando se añada autenticación
    # user = getattr(request.state, 'user', None)
    # return str(user.id) if user else None
    return None


def create_limiter() -> Limiter:
    """
    Crear y configurar el limitador de rate limiting.
    """
    def combined_key_func(request: Request) -> str:
        """
        Función de clave combinada para rate limiting.
        Prioriza usuario autenticado, fallback a IP.
        """
        user_id = get_authenticated_user_id(request)
        if user_id:
            return f"user:{user_id}"

        client_ip = get_client_identifier(request)
        return f"ip:{client_ip}"

    # Obtener storage URI desde configuración
    from ..core.config import settings
    storage_uri = getattr(settings, 'rate_limit_storage_uri', "memory://")

    limiter = Limiter(
        key_func=combined_key_func,
        storage_uri=storage_uri,
        default_limits=["1000/hour"],  # Límite por defecto
        headers_enabled=True,  # Incluir headers de rate limiting en respuestas
    )

    return limiter


# Instancia global del limitador
limiter = create_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> HTTPException:
    """
    Handler personalizado para rate limit exceeded.
    """
    client_id = get_client_identifier(request)
    logger.warning(
        f"Rate limit exceeded for client {client_id}: "
        f"{exc.detail}. Headers: {dict(request.headers)}"
    )

    # Registrar métricas de rate limiting
    try:
        from .metrics import metrics_collector
        metrics_collector.increment_counter(
            "rate_limit_exceeded_total",
            tags={
                "client_ip": client_id,
                "endpoint": str(request.url.path),
                "method": request.method
            }
        )
    except ImportError:
        pass  # Metrics collector no disponible

    return HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after,
            "limit": exc.detail
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.detail.split('/')[0]),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.retry_after)
        }
    )


# Rate limits específicos por endpoint

# Scraping - muy restrictivo para evitar abuso
SCRAPING_LIMITS = [
    "10/minute",  # Máximo 10 requests de scraping por minuto
    "100/hour",   # Máximo 100 requests de scraping por hora
    "500/day"     # Máximo 500 requests de scraping por día
]

# API de gestión de datos - moderadamente restrictivo
DATA_MANAGEMENT_LIMITS = [
    "60/minute",  # 60 requests por minuto
    "1000/hour"   # 1000 requests por hora
]

# Endpoints de monitoreo - menos restrictivo
MONITORING_LIMITS = [
    "100/minute",  # 100 requests por minuto
    "2000/hour"    # 2000 requests por hora
]

# Observabilidad - muy permisivo para health checks
OBSERVABILITY_LIMITS = [
    "200/minute",  # 200 requests por minuto
    "5000/hour"    # 5000 requests por hora
]


def get_rate_limits_for_endpoint(endpoint_path: str) -> list[str]:
    """
    Obtener límites de rate limiting específicos para un endpoint.
    """
    if endpoint_path.startswith("/scraper"):
        return SCRAPING_LIMITS
    elif endpoint_path.startswith("/api"):
        return DATA_MANAGEMENT_LIMITS
    elif endpoint_path.startswith("/monitoring"):
        return MONITORING_LIMITS
    elif endpoint_path.startswith("/observability"):
        return OBSERVABILITY_LIMITS
    else:
        return ["100/minute", "1000/hour"]  # Límites por defecto


class RateLimitingMiddleware:
    """
    Middleware personalizado para rate limiting con logging y métricas.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Crear request object para análisis
        request = Request(scope, receive)

        # Log de request para debugging
        client_id = get_client_identifier(request)
        logger.debug(
            f"Request from {client_id}: {request.method} {request.url.path}"
        )

        # Registrar métricas de requests
        try:
            from .metrics import metrics_collector
            metrics_collector.increment_counter(
                "api_requests_total",
                tags={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "client_ip": client_id
                }
            )
        except ImportError:
            pass

        await self.app(scope, receive, send)


def setup_rate_limiting(app):
    """
    Configurar rate limiting en la aplicación FastAPI.
    """
    # Añadir middleware de SlowAPI
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Añadir middleware personalizado
    app.add_middleware(RateLimitingMiddleware)

    # Añadir middleware de SlowAPI
    app.add_middleware(SlowAPIMiddleware)

    logger.info("Rate limiting configured successfully")

    return limiter


# Decorador para proteger funciones específicas
def rate_limit(*limits: str):
    """
    Decorador para aplicar rate limiting a funciones específicas.

    Usage:
        @rate_limit("10/minute", "100/hour")
        async def protected_function():
            pass
    """
    def decorator(func):
        # Aplicar límites usando slowapi
        for limit in limits:
            func = limiter.limit(limit)(func)
        return func
    return decorator


# Funciones de utilidad para verificar límites

async def check_rate_limit(request: Request, limit: str) -> bool:
    """
    Verificar si un request excede el rate limit sin aplicarlo.
    Útil para warnings preventivos.
    """
    try:
        # Simular verificación de límite
        key = get_client_identifier(request)
        # Esta sería la lógica real de verificación
        # Por ahora siempre retorna True (no excedido)
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True  # En caso de error, permitir el request


async def get_rate_limit_status(request: Request) -> Dict[str, Any]:
    """
    Obtener estado actual de rate limiting para un cliente.
    """
    client_id = get_client_identifier(request)

    return {
        "client_id": client_id,
        "limits": {
            "scraping": SCRAPING_LIMITS,
            "data_management": DATA_MANAGEMENT_LIMITS,
            "monitoring": MONITORING_LIMITS,
            "observability": OBSERVABILITY_LIMITS
        },
        "current_usage": {
            # TODO: Implementar consulta de uso actual
            "requests_last_minute": 0,
            "requests_last_hour": 0,
            "requests_last_day": 0
        }
    }


# Configuración para producción con Redis
def create_production_limiter(redis_url: str = "redis://localhost:6379") -> Limiter:
    """
    Crear limitador para producción usando Redis como storage.
    """
    def combined_key_func(request: Request) -> str:
        user_id = get_authenticated_user_id(request)
        if user_id:
            return f"user:{user_id}"
        return f"ip:{get_client_identifier(request)}"

    return Limiter(
        key_func=combined_key_func,
        storage_uri=redis_url,
        default_limits=["1000/hour"],
        headers_enabled=True,
    )