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
from backend.routes import gestion_datos, scraper, monitoring, observability
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
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    setup_signal_handlers()
    register_all_shutdown_callbacks()
    register_all_health_checks()
    register_event_handlers()
    await start_scheduler()

    # Iniciar tareas de limpieza con graceful shutdown
    async with shutdown_manager.managed_task(periodic_cache_cleanup()) as cache_task:
        async with shutdown_manager.managed_task(periodic_metrics_cleanup()) as metrics_task:
            yield

    # Graceful shutdown
    stop_scheduler()
    await shutdown_manager.shutdown()


app = FastAPI(
    title="Arbitraje Minorista API",
    version="0.1.0",
    description="API para el seguimiento de productos y oportunidades de arbitraje.",
    lifespan=lifespan
)


# --- Middlewares ---
# Los middlewares se ejecutan en orden inverso de como se añaden.
# 1. El de errores debe ser el más externo (el último que se añade).
# 2. El de CORS y otros van después.
# 3. El de logging y correlation ID debe ser el más interno (el primero que se añade).

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3030"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(add_process_time_and_correlation_id)


# --- Exception Handlers ---
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Arbitraje Minorista"}


# --- Routers ---
app.include_router(gestion_datos.router)
app.include_router(scraper.router)
app.include_router(monitoring.router)
app.include_router(observability.router)
