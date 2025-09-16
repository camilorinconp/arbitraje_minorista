# backend/repositories/minorista_repository.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from ..models.minorista import Minorista


class MinoristaRepository(BaseRepository[Minorista]):
    """
    Repositorio específico para operaciones de minoristas.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Minorista)

    async def get_active_retailers(self) -> List[Minorista]:
        """Obtener todos los minoristas activos."""
        try:
            stmt = select(Minorista).where(Minorista.activo == True)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_retailers_with_discovery_config(self) -> List[Minorista]:
        """Obtener minoristas activos con configuración de descubrimiento."""
        try:
            stmt = select(Minorista).where(
                Minorista.activo == True,
                Minorista.discovery_url.isnot(None),
                Minorista.product_link_selector.isnot(None)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_retailers_with_scraping_config(self) -> List[Minorista]:
        """Obtener minoristas con configuración completa de scraping."""
        try:
            stmt = select(Minorista).where(
                Minorista.activo == True,
                Minorista.name_selector.isnot(None),
                Minorista.price_selector.isnot(None)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_by_name(self, nombre: str) -> Optional[Minorista]:
        """Obtener minorista por nombre."""
        try:
            stmt = select(Minorista).where(Minorista.nombre == nombre)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def update_selectors(self, id: int, name_selector: str,
                             price_selector: str, image_selector: Optional[str] = None) -> Optional[Minorista]:
        """Actualizar selectores de scraping de un minorista."""
        try:
            retailer = await self.get_by_id(id)
            if retailer:
                retailer.name_selector = name_selector
                retailer.price_selector = price_selector
                if image_selector:
                    retailer.image_selector = image_selector
                return await self.update(retailer)
            return None
        except SQLAlchemyError as e:
            raise e

    async def toggle_active_status(self, id: int) -> Optional[Minorista]:
        """Cambiar estado activo/inactivo de un minorista."""
        try:
            retailer = await self.get_by_id(id)
            if retailer:
                retailer.activo = not retailer.activo
                return await self.update(retailer)
            return None
        except SQLAlchemyError as e:
            raise e