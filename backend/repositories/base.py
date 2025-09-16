# backend/repositories/base.py

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """
    Repositorio base que define operaciones CRUD comunes.
    """

    def __init__(self, db: AsyncSession, model_class: type):
        self.db = db
        self.model_class = model_class

    async def get_by_id(self, id: int) -> Optional[T]:
        """Obtener entidad por ID."""
        try:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Obtener todas las entidades con paginación opcional."""
        try:
            stmt = select(self.model_class)
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e

    async def create(self, entity: T) -> T:
        """Crear nueva entidad."""
        try:
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def update(self, entity: T) -> T:
        """Actualizar entidad existente."""
        try:
            self.db.add(entity)
            await self.db.commit()
            await self.db.refresh(entity)
            return entity
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def delete(self, id: int) -> bool:
        """Eliminar entidad por ID."""
        try:
            entity = await self.get_by_id(id)
            if entity:
                await self.db.delete(entity)
                await self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def exists(self, id: int) -> bool:
        """Verificar si existe entidad por ID."""
        entity = await self.get_by_id(id)
        return entity is not None