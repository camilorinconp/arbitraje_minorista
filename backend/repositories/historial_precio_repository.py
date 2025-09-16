# backend/repositories/historial_precio_repository.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models.historial_precio import HistorialPrecio


class HistorialPrecioRepository(BaseRepository[HistorialPrecio]):
    """
    Repositorio específico para operaciones de historial de precios.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, HistorialPrecio)

    async def get_history_by_product(self, id_producto: int, limit: int = 100) -> List[HistorialPrecio]:
        """Obtener historial de precios de un producto específico."""
        try:
            stmt = (
                select(HistorialPrecio)
                .where(HistorialPrecio.id_producto == id_producto)
                .order_by(desc(HistorialPrecio.fecha_registro))
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_history_by_retailer(self, id_minorista: int, limit: int = 100) -> List[HistorialPrecio]:
        """Obtener historial de precios de un minorista específico."""
        try:
            stmt = (
                select(HistorialPrecio)
                .where(HistorialPrecio.id_minorista == id_minorista)
                .order_by(desc(HistorialPrecio.fecha_registro))
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_recent_history(self, hours: int = 24) -> List[HistorialPrecio]:
        """Obtener historial de precios reciente."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            stmt = (
                select(HistorialPrecio)
                .where(HistorialPrecio.fecha_registro >= cutoff_time)
                .order_by(desc(HistorialPrecio.fecha_registro))
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def create_price_record(self, id_producto: int, id_minorista: int, precio: float) -> HistorialPrecio:
        """Crear nuevo registro de precio."""
        try:
            new_record = HistorialPrecio(
                id_producto=id_producto,
                id_minorista=id_minorista,
                precio=precio,
                fecha_registro=datetime.now()
            )
            return await self.create(new_record)
        except SQLAlchemyError as e:
            raise e

    async def get_latest_price(self, id_producto: int, id_minorista: int) -> Optional[HistorialPrecio]:
        """Obtener el precio más reciente de un producto en un minorista."""
        try:
            stmt = (
                select(HistorialPrecio)
                .where(
                    HistorialPrecio.id_producto == id_producto,
                    HistorialPrecio.id_minorista == id_minorista
                )
                .order_by(desc(HistorialPrecio.fecha_registro))
                .limit(1)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def get_price_changes(self, id_producto: int, days: int = 30) -> List[HistorialPrecio]:
        """Obtener cambios de precio de un producto en los últimos X días."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            stmt = (
                select(HistorialPrecio)
                .where(
                    HistorialPrecio.id_producto == id_producto,
                    HistorialPrecio.fecha_registro >= cutoff_time
                )
                .order_by(HistorialPrecio.fecha_registro)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e