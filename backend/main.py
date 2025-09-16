from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.error_handling import (
    add_process_time_and_correlation_id,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from .core.scheduler import start_scheduler, stop_scheduler
from .routes import gestion_datos, scraper

app = FastAPI(
    title="Arbitraje Minorista API",
    version="0.1.0",
    description="API para el seguimiento de productos y oportunidades de arbitraje.",
)

# --- Ciclo de Vida del Planificador ---
@app.on_event("startup")
async def on_startup():
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


# --- Middlewares ---
# Los middlewares se ejecutan en orden inverso de como se añaden.
# 1. El de errores debe ser el más externo (el último que se añade).
# 2. El de CORS y otros van después.
# 3. El de logging y correlation ID debe ser el más interno (el primero que se añade).

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3030"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
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