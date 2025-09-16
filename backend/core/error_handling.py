# backend/core/error_handling.py

import time
import uuid
import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configuración básica del logger para este módulo
# Más adelante lo reemplazaremos por un logger estructurado en la Tarea 2.2
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.errors")


async def http_exception_handler(request: Request, exc: Exception):
    """Manejador para excepciones HTTP generales."""
    correlation_id = request.state.correlation_id
    logger.error(
        f"HTTP Exception: {exc.status_code} {exc.detail}",
        extra={"correlation_id": correlation_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "HTTP_EXCEPTION",
                "message": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": correlation_id,
            },
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador para errores de validación de Pydantic."""
    correlation_id = request.state.correlation_id
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Omitir 'body'
        errors.append({"field": field, "message": error["msg"]})

    logger.warning(
        f"Validation Error: {errors}",
        extra={"correlation_id": correlation_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "type": "VALIDATION_ERROR",
                "message": "Error de validación en los datos de entrada.",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "correlation_id": correlation_id,
                "details": errors,
            },
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Manejador para cualquier otra excepción no capturada."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4())[:8])
    logger.critical(
        f"Unhandled Exception: {exc}",
        extra={"correlation_id": correlation_id, "path": request.url.path},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "type": "INTERNAL_SERVER_ERROR",
                "message": "Ha ocurrido un error inesperado en el servidor.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "correlation_id": correlation_id,
            },
        },
    )


async def add_process_time_and_correlation_id(request: Request, call_next):
    """Middleware para añadir el ID de correlación y medir el tiempo de proceso."""
    start_time = time.time()
    # Asignar un ID único a cada petición
    correlation_id = str(uuid.uuid4())[:8]
    request.state.correlation_id = correlation_id

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    response.headers["X-Correlation-ID"] = correlation_id

    logger.info(
        "Request handled",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        },
    )

    return response
