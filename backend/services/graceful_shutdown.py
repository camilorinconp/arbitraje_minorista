# backend/services/graceful_shutdown.py

import asyncio
import logging
import signal
from typing import List, Callable, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class GracefulShutdownManager:
    """
    Manager para manejo graceful de shutdown con cleanup de recursos.
    """

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds
        self.shutdown_callbacks: List[Callable] = []
        self.is_shutting_down = False
        self._shutdown_event = asyncio.Event()
        self._cleanup_tasks: List[asyncio.Task] = []

    def register_shutdown_callback(self, callback: Callable):
        """Registrar callback para ejecutar durante shutdown."""
        self.shutdown_callbacks.append(callback)
        logger.info(f"Shutdown callback registered: {callback.__name__}")

    async def shutdown(self):
        """Ejecutar graceful shutdown."""
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress")
            return

        self.is_shutting_down = True
        logger.info("Starting graceful shutdown...")

        try:
            # Ejecutar callbacks de shutdown
            for callback in self.shutdown_callbacks:
                try:
                    logger.info(f"Executing shutdown callback: {callback.__name__}")
                    if asyncio.iscoroutinefunction(callback):
                        await asyncio.wait_for(callback(), timeout=5.0)
                    else:
                        callback()
                except asyncio.TimeoutError:
                    logger.error(f"Shutdown callback {callback.__name__} timed out")
                except Exception as e:
                    logger.error(f"Error in shutdown callback {callback.__name__}: {e}")

            # Cancelar y esperar cleanup tasks
            if self._cleanup_tasks:
                logger.info(f"Cancelling {len(self._cleanup_tasks)} cleanup tasks")
                for task in self._cleanup_tasks:
                    task.cancel()

                # Esperar que terminen las tasks canceladas
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._cleanup_tasks, return_exceptions=True),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some cleanup tasks did not finish in time")

            # Cerrar connections de database
            from .database import async_engine
            await async_engine.dispose()

            logger.info("Graceful shutdown completed")

        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
        finally:
            self._shutdown_event.set()

    async def wait_for_shutdown(self):
        """Esperar hasta que se complete el shutdown."""
        await self._shutdown_event.wait()

    def add_cleanup_task(self, task: asyncio.Task):
        """Agregar task para cleanup durante shutdown."""
        self._cleanup_tasks.append(task)

    @asynccontextmanager
    async def managed_task(self, coro):
        """Context manager para tasks que necesitan cleanup."""
        task = asyncio.create_task(coro)
        self.add_cleanup_task(task)
        try:
            yield task
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


# Instancia global
shutdown_manager = GracefulShutdownManager()


def setup_signal_handlers():
    """Configurar handlers para señales del sistema."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        # Crear task para shutdown async
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(shutdown_manager.shutdown())
        else:
            asyncio.run(shutdown_manager.shutdown())

    # Registrar handlers para SIGTERM y SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Signal handlers configured for graceful shutdown")


async def shutdown_cleanup_cache():
    """Cleanup específico para cache."""
    from .cache import app_cache
    logger.info("Cleaning up cache...")
    await app_cache.clear()
    logger.info("Cache cleanup completed")


async def shutdown_cleanup_metrics():
    """Cleanup específico para métricas."""
    from .metrics import metrics_collector
    logger.info("Cleaning up metrics...")
    metrics_collector.cleanup_old_metrics()
    logger.info("Metrics cleanup completed")


def register_all_shutdown_callbacks():
    """Registrar todos los callbacks de shutdown."""
    shutdown_manager.register_shutdown_callback(shutdown_cleanup_cache)
    shutdown_manager.register_shutdown_callback(shutdown_cleanup_metrics)
    logger.info("All shutdown callbacks registered")