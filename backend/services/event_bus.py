# backend/services/event_bus.py

import asyncio
import logging
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Tipos de eventos del sistema."""
    PRODUCT_SCRAPED = "product_scraped"
    PRODUCT_UPDATED = "product_updated"
    PRICE_CHANGED = "price_changed"
    RETAILER_CREATED = "retailer_created"
    RETAILER_UPDATED = "retailer_updated"
    SCRAPING_STARTED = "scraping_started"
    SCRAPING_COMPLETED = "scraping_completed"
    SCRAPING_FAILED = "scraping_failed"


@dataclass
class Event:
    """Estructura base de un evento."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "system"
    event_id: str = None

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = f"{self.type.value}_{self.timestamp.isoformat()}"


class EventBus:
    """
    Bus de eventos para comunicación desacoplada entre servicios.
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000

    async def publish(self, event: Event) -> None:
        """Publicar un evento en el bus."""
        logger.info(f"Publishing event: {event.type.value} from {event.source}")

        # Guardar en historial
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Ejecutar handlers registrados
        handlers = self._handlers.get(event.type, [])
        if handlers:
            # Ejecutar todos los handlers concurrentemente
            tasks = []
            for handler in handlers:
                task = asyncio.create_task(self._execute_handler(handler, event))
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.debug(f"No handlers registered for event type: {event.type.value}")

    async def _execute_handler(self, handler: Callable, event: Event) -> None:
        """Ejecutar un handler de forma segura."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Error executing event handler for {event.type.value}: {e}", exc_info=True)

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Suscribirse a un tipo de evento."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.info(f"Handler registered for event type: {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Desuscribirse de un tipo de evento."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Handler unregistered for event type: {event_type.value}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type.value}")

    def get_event_history(self, limit: int = 100) -> List[Event]:
        """Obtener historial de eventos."""
        return self._event_history[-limit:]

    def get_handlers_count(self, event_type: EventType) -> int:
        """Obtener número de handlers registrados para un tipo de evento."""
        return len(self._handlers.get(event_type, []))


# Instancia global del bus de eventos
event_bus = EventBus()