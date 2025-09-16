# backend/services/cache.py

import asyncio
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrada de cache con metadatos."""
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class MemoryCache:
    """
    Cache en memoria optimizado para consultas frecuentes.
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # Para LRU
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Verificar expiración
            if datetime.now() >= entry.expires_at:
                await self._remove_key(key)
                return None

            # Actualizar estadísticas de acceso
            entry.access_count += 1
            entry.last_accessed = datetime.now()

            # Actualizar orden LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            logger.debug(f"Cache hit for key: {key}")
            return entry.data

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Establecer valor en el cache."""
        async with self._lock:
            ttl = ttl_seconds or self.default_ttl
            now = datetime.now()

            entry = CacheEntry(
                data=value,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
                access_count=1,
                last_accessed=now
            )

            # Si existe, actualizar
            if key in self._cache:
                self._cache[key] = entry
            else:
                # Si está lleno, remover el menos usado (LRU)
                if len(self._cache) >= self.max_size:
                    await self._evict_lru()

                self._cache[key] = entry

            # Actualizar orden LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")

    async def delete(self, key: str) -> bool:
        """Eliminar entrada del cache."""
        async with self._lock:
            if key in self._cache:
                await self._remove_key(key)
                logger.debug(f"Cache delete for key: {key}")
                return True
            return False

    async def clear(self) -> None:
        """Limpiar todo el cache."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("Cache cleared")

    async def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache."""
        async with self._lock:
            total_entries = len(self._cache)
            expired_count = 0
            now = datetime.now()

            for entry in self._cache.values():
                if now >= entry.expires_at:
                    expired_count += 1

            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "max_size": self.max_size,
                "usage_percentage": (total_entries / self.max_size) * 100,
                "memory_efficiency": ((total_entries - expired_count) / total_entries * 100) if total_entries > 0 else 0
            }

    async def _remove_key(self, key: str) -> None:
        """Remover clave del cache y orden LRU."""
        if key in self._cache:
            del self._cache[key]
        if key in self._access_order:
            self._access_order.remove(key)

    async def _evict_lru(self) -> None:
        """Eliminar el elemento menos recientemente usado."""
        if self._access_order:
            lru_key = self._access_order[0]
            await self._remove_key(lru_key)
            logger.debug(f"Evicted LRU key: {lru_key}")

    async def cleanup_expired(self) -> int:
        """Limpiar entradas expiradas. Retorna número de entradas eliminadas."""
        async with self._lock:
            now = datetime.now()
            expired_keys = []

            for key, entry in self._cache.items():
                if now >= entry.expires_at:
                    expired_keys.append(key)

            for key in expired_keys:
                await self._remove_key(key)

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)


class QueryCache:
    """
    Cache especializado para consultas de base de datos.
    """

    def __init__(self, cache: MemoryCache):
        self.cache = cache

    def _generate_query_key(self, query_name: str, params: Dict[str, Any]) -> str:
        """Generar clave única para una consulta."""
        # Serializar parámetros de forma consistente
        params_str = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{query_name}:{params_str}"
        # Usar hash para claves más cortas
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get_query_result(self, query_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """Obtener resultado de consulta cacheado."""
        key = self._generate_query_key(query_name, params)
        return await self.cache.get(key)

    async def cache_query_result(
        self, query_name: str, params: Dict[str, Any], result: Any, ttl_seconds: int = 300
    ) -> None:
        """Cachear resultado de consulta."""
        key = self._generate_query_key(query_name, params)
        await self.cache.set(key, result, ttl_seconds)

    async def invalidate_query_pattern(self, query_name: str) -> int:
        """Invalidar todas las consultas que coincidan con un patrón."""
        # Esta es una implementación simple que limpia todo el cache
        # En una implementación más sofisticada, se podrían usar prefijos
        await self.cache.clear()
        return 0


# Cache global para la aplicación
app_cache = MemoryCache(max_size=2000, default_ttl_seconds=600)  # 10 minutos por defecto
query_cache = QueryCache(app_cache)


# Task para limpiar cache expirado periódicamente
async def periodic_cache_cleanup():
    """Tarea para limpiar el cache expirado cada 5 minutos."""
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutos
            cleaned = await app_cache.cleanup_expired()
            if cleaned > 0:
                logger.info(f"Periodic cache cleanup: removed {cleaned} expired entries")
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}", exc_info=True)