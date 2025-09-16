# backend/repositories/__init__.py

from .base import BaseRepository
from .producto_repository import ProductoRepository
from .minorista_repository import MinoristaRepository
from .historial_precio_repository import HistorialPrecioRepository

__all__ = [
    "BaseRepository",
    "ProductoRepository",
    "MinoristaRepository",
    "HistorialPrecioRepository"
]