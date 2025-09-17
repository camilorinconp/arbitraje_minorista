from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from backend.core.error_handling import (
    add_process_time_and_correlation_id,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.core.scheduler import start_scheduler, stop_scheduler
from backend.routes import gestion_datos, scraper, monitoring, observability, rate_limit_status
from backend.services.event_handlers import register_event_handlers
from backend.services.cache import periodic_cache_cleanup
from backend.services.logging_config import setup_logging
from backend.services.health_checks import register_all_health_checks
from backend.services.metrics import periodic_metrics_cleanup
from backend.services.graceful_shutdown import (
    shutdown_manager,
    setup_signal_handlers,
    register_all_shutdown_callbacks
)
from backend.services.rate_limiter import setup_rate_limiting
from backend.core.config import settings, validate_production_config
import asyncio
import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger = logging.getLogger(__name__)

    # Validate production configuration
    if settings.is_production:
        config_errors = validate_production_config()
        if config_errors:
            logger.error("Production configuration errors:")
            for error in config_errors:
                logger.error(f"  - {error}")
            raise RuntimeError("Invalid production configuration")

    logger.info(f"Starting {settings.app_name} v{settings.app_version} in {settings.app_env} mode")

    setup_logging()
    setup_signal_handlers()
    register_all_shutdown_callbacks()
    register_all_health_checks()
    register_event_handlers()

    if settings.scheduler_enabled:
        await start_scheduler()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler disabled by configuration")

    # Iniciar tareas de limpieza con graceful shutdown
    async with shutdown_manager.managed_task(periodic_cache_cleanup()) as cache_task:
        async with shutdown_manager.managed_task(periodic_metrics_cleanup()) as metrics_task:
            yield

    # Graceful shutdown
    stop_scheduler()
    await shutdown_manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API para el seguimiento de productos y oportunidades de arbitraje.",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_redoc else None,
    openapi_url="/openapi.json" if settings.enable_docs else None
)


# --- Middlewares ---
# Los middlewares se ejecutan en orden inverso de como se añaden.
# 1. El de errores debe ser el más externo (el último que se añade).
# 2. El de CORS y otros van después.
# 3. El de logging y correlation ID debe ser el más interno (el primero que se añade).

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_for_env(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(add_process_time_and_correlation_id)

# --- Rate Limiting ---
setup_rate_limiting(app)


# --- Exception Handlers ---
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/")
def read_root():
    return {
        "message": f"Bienvenido a {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.app_env.value,
        "status": "running"
    }


@app.get("/config")
def get_config_info():
    """Obtener información de configuración (sin secrets)."""
    from backend.core.config import get_environment_info
    return get_environment_info()


# --- Routers ---
app.include_router(gestion_datos.router)
app.include_router(scraper.router)
app.include_router(monitoring.router)
app.include_router(observability.router)
app.include_router(rate_limit_status.router)

# Authentication router
from backend.routes import auth
app.include_router(auth.router)
