# backend/services/logging_config.py

import logging
import logging.config
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
from contextvars import ContextVar

# Context variable para correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Formatter que produce logs estructurados en formato JSON.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Agregar correlation ID si existe
        corr_id = correlation_id.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id

        # Agregar información de excepción si existe
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Agregar campos personalizados si existen
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class PerformanceLogger:
    """
    Logger especializado para métricas de performance.
    """

    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)

    def log_operation_duration(
        self,
        operation: str,
        duration_seconds: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log de duración de operaciones."""
        extra_fields = {
            "operation": operation,
            "duration_seconds": duration_seconds,
            "success": success,
            "performance_metric": True
        }

        if metadata:
            extra_fields.update(metadata)

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"Operation '{operation}' completed in {duration_seconds:.3f}s",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)

    def log_scraping_metrics(
        self,
        total_products: int,
        successful: int,
        failed: int,
        duration: float,
        products_per_second: float
    ):
        """Log de métricas de scraping."""
        extra_fields = {
            "scraping_metrics": {
                "total_products": total_products,
                "successful": successful,
                "failed": failed,
                "duration_seconds": duration,
                "products_per_second": products_per_second,
                "success_rate": (successful / total_products * 100) if total_products > 0 else 0
            },
            "performance_metric": True
        }

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"Scraping completed: {successful}/{total_products} products in {duration:.2f}s",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


class BusinessLogger:
    """
    Logger especializado para eventos de negocio.
    """

    def __init__(self, logger_name: str = "business"):
        self.logger = logging.getLogger(logger_name)

    def log_price_change(
        self,
        product_id: int,
        product_name: str,
        old_price: float,
        new_price: float,
        retailer_id: int
    ):
        """Log de cambios de precio."""
        change_amount = new_price - old_price
        change_percentage = (change_amount / old_price * 100) if old_price > 0 else 0

        extra_fields = {
            "business_event": "price_change",
            "product_id": product_id,
            "product_name": product_name,
            "retailer_id": retailer_id,
            "price_data": {
                "old_price": old_price,
                "new_price": new_price,
                "change_amount": change_amount,
                "change_percentage": change_percentage
            }
        }

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"Price change detected for '{product_name}': ${old_price} -> ${new_price} ({change_percentage:+.1f}%)",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)

    def log_product_discovery(self, retailer_name: str, products_found: int, new_products: int):
        """Log de descubrimiento de productos."""
        extra_fields = {
            "business_event": "product_discovery",
            "retailer_name": retailer_name,
            "products_found": products_found,
            "new_products": new_products
        }

        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn="",
            lno=0,
            msg=f"Product discovery for {retailer_name}: {products_found} found, {new_products} new",
            args=(),
            exc_info=None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)


def setup_logging():
    """
    Configurar el sistema de logging estructurado.
    """
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "structured",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "structured",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "performance": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": "logs/performance.log",
                "maxBytes": 10485760,
                "backupCount": 3
            },
            "business": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "structured",
                "filename": "logs/business.log",
                "maxBytes": 10485760,
                "backupCount": 3
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": "INFO",
                "handlers": ["console", "file"]
            },
            "performance": {
                "level": "INFO",
                "handlers": ["performance"],
                "propagate": False
            },
            "business": {
                "level": "INFO",
                "handlers": ["business"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "WARNING",  # Reducir logs de SQL en producción
                "handlers": ["file"],
                "propagate": False
            }
        }
    }

    # Crear directorio de logs si no existe
    import os
    os.makedirs("logs", exist_ok=True)

    logging.config.dictConfig(logging_config)


def set_correlation_id(corr_id: str = None) -> str:
    """Establecer correlation ID para el contexto actual."""
    if corr_id is None:
        corr_id = str(uuid.uuid4())
    correlation_id.set(corr_id)
    return corr_id


def get_correlation_id() -> Optional[str]:
    """Obtener correlation ID del contexto actual."""
    return correlation_id.get()


# Instancias globales de loggers especializados
performance_logger = PerformanceLogger()
business_logger = BusinessLogger()