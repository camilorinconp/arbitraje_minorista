# backend/repositories/producto_repository.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models.producto import Producto
from ..models.minorista import Minorista
from ..services.cache import query_cache


class ProductoRepository(BaseRepository[Producto]):
    """
    Repositorio específico para operaciones de productos.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Producto)

    async def get_by_url_and_retailer(self, product_url: str, id_minorista: int) -> Optional[Producto]:
        """Obtener producto por URL y minorista."""
        try:
            stmt = select(Producto).where(
                Producto.product_url == product_url,
                Producto.id_minorista == id_minorista
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def get_products_by_retailer(self, id_minorista: int) -> List[Producto]:
        """Obtener todos los productos de un minorista específico."""
        try:
            stmt = select(Producto).where(Producto.id_minorista == id_minorista)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def get_products_from_active_retailers(self) -> List[Producto]:
        """Obtener productos de minoristas activos."""
        cache_key = "products_from_active_retailers"

        # Intentar obtener del cache primero
        cached_result = await query_cache.get_query_result(cache_key, {})
        if cached_result is not None:
            return cached_result

        try:
            stmt = (
                select(Producto)
                .join(Minorista)
                .where(Minorista.activo == True)
            )
            result = await self.db.execute(stmt)
            products = result.scalars().all()

            # Cachear resultado por 5 minutos
            await query_cache.cache_query_result(cache_key, {}, products, ttl_seconds=300)

            return products
        except SQLAlchemyError as e:
            raise e

    async def get_recently_scraped_products(self, hours: int = 24) -> List[Producto]:
        """Obtener productos scrapeados en las últimas X horas."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            stmt = select(Producto).where(Producto.last_scraped_at >= cutoff_time)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def update_scraped_data(self, product_url: str, id_minorista: int,
                                name: str, price: float, image_url: Optional[str] = None) -> Producto:
        """Actualizar o crear producto con datos de scraping."""
        try:
            existing_product = await self.get_by_url_and_retailer(product_url, id_minorista)
            current_time = datetime.now()

            if existing_product:
                # Actualizar producto existente
                existing_product.name = name
                existing_product.price = price
                existing_product.image_url = image_url
                existing_product.last_scraped_at = current_time
                return await self.update(existing_product)
            else:
                # Crear nuevo producto
                new_product = Producto(
                    name=name,
                    price=price,
                    product_url=product_url,
                    image_url=image_url,
                    last_scraped_at=current_time,
                    id_minorista=id_minorista,
                    identificador_producto=None
                )
                return await self.create(new_product)
        except SQLAlchemyError as e:
            raise e

    async def search_by_name(self, search_term: str, limit: int = 50) -> List[Producto]:
        """Buscar productos por nombre."""
        try:
            stmt = (
                select(Producto)
                .where(Producto.name.ilike(f"%{search_term}%"))
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e