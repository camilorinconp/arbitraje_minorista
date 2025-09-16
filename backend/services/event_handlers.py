# backend/services/event_handlers.py

import logging
from datetime import datetime
from typing import Dict, Any

from .event_bus import Event, EventType, event_bus
from ..repositories import HistorialPrecioRepository
from ..services.database import AsyncSessionLocal
from .logging_config import business_logger, performance_logger
from .metrics import metrics_collector

logger = logging.getLogger(__name__)


class ScrapingEventHandlers:
    """Handlers para eventos relacionados con scraping."""

    @staticmethod
    async def on_product_scraped(event: Event) -> None:
        """Handler para cuando se scrapea un producto."""
        try:
            data = event.data
            product_id = data.get("product_id")
            retailer_id = data.get("retailer_id")
            product_name = data.get("product_name")
            price = data.get("price")
            old_price = data.get("old_price")
            is_new_product = data.get("is_new_product", False)

            logger.info(f"Product scraped: ID {product_id}, Price: {price}")

            # Métricas de scraping
            metrics_collector.increment_counter("products.scraped", 1, {"retailer_id": str(retailer_id)})

            if is_new_product:
                metrics_collector.increment_counter("products.discovered", 1, {"retailer_id": str(retailer_id)})

            # Si hay cambio de precio, publicar evento específico y registrar métricas
            if old_price is not None and old_price != price:
                change_amount = price - old_price
                change_percentage = ((price - old_price) / old_price) * 100 if old_price > 0 else 0

                # Log de negocio para cambio de precio
                business_logger.log_price_change(
                    product_id=product_id,
                    product_name=product_name,
                    old_price=old_price,
                    new_price=price,
                    retailer_id=retailer_id
                )

                # Métricas de cambio de precio
                metrics_collector.increment_counter("price_changes.total", 1)
                if abs(change_percentage) > 10:
                    metrics_collector.increment_counter("price_changes.significant", 1)

                price_change_event = Event(
                    type=EventType.PRICE_CHANGED,
                    data={
                        "product_id": product_id,
                        "retailer_id": retailer_id,
                        "product_name": product_name,
                        "old_price": old_price,
                        "new_price": price,
                        "change_amount": change_amount,
                        "change_percentage": change_percentage
                    },
                    timestamp=datetime.now(),
                    source="scraping_handler"
                )
                await event_bus.publish(price_change_event)

        except Exception as e:
            logger.error(f"Error in on_product_scraped handler: {e}", exc_info=True)
            metrics_collector.increment_counter("event_handlers.errors", 1, {"handler": "on_product_scraped"})

    @staticmethod
    async def on_price_changed(event: Event) -> None:
        """Handler para cuando cambia el precio de un producto."""
        try:
            data = event.data
            product_id = data.get("product_id")
            old_price = data.get("old_price")
            new_price = data.get("new_price")
            change_percentage = data.get("change_percentage", 0)

            logger.info(f"Price changed for product {product_id}: ${old_price} -> ${new_price} ({change_percentage:.2f}%)")

            # Lógica adicional para cambios significativos de precio
            if abs(change_percentage) > 10:  # Cambio mayor al 10%
                logger.warning(f"Significant price change detected for product {product_id}: {change_percentage:.2f}%")
                # Aquí se podría enviar notificaciones, alertas, etc.

        except Exception as e:
            logger.error(f"Error in on_price_changed handler: {e}", exc_info=True)

    @staticmethod
    async def on_scraping_completed(event: Event) -> None:
        """Handler para cuando se completa el scraping."""
        try:
            data = event.data
            duration = data.get("duration_seconds", 0)
            products_processed = data.get("products_processed", 0)
            errors_count = data.get("errors_count", 0)
            successful = data.get("successful", products_processed - errors_count)

            logger.info(f"Scraping completed: {products_processed} products in {duration:.2f}s, {errors_count} errors")

            # Métricas de performance
            products_per_second = products_processed / duration if duration > 0 else 0
            success_rate = (successful / products_processed * 100) if products_processed > 0 else 0

            # Log de performance
            performance_logger.log_scraping_metrics(
                total_products=products_processed,
                successful=successful,
                failed=errors_count,
                duration=duration,
                products_per_second=products_per_second
            )

            # Métricas del sistema
            metrics_collector.set_gauge("scraping.last_duration_seconds", duration)
            metrics_collector.set_gauge("scraping.last_products_processed", products_processed)
            metrics_collector.set_gauge("scraping.last_success_rate", success_rate)
            metrics_collector.set_gauge("scraping.products_per_second", products_per_second)
            metrics_collector.increment_counter("scraping.completed", 1)

            logger.info(f"Scraping success rate: {success_rate:.1f}%, {products_per_second:.2f} products/sec")

        except Exception as e:
            logger.error(f"Error in on_scraping_completed handler: {e}", exc_info=True)
            metrics_collector.increment_counter("event_handlers.errors", 1, {"handler": "on_scraping_completed"})


class RetailerEventHandlers:
    """Handlers para eventos relacionados con minoristas."""

    @staticmethod
    async def on_retailer_created(event: Event) -> None:
        """Handler para cuando se crea un minorista."""
        try:
            data = event.data
            retailer_id = data.get("retailer_id")
            retailer_name = data.get("retailer_name")

            logger.info(f"New retailer created: {retailer_name} (ID: {retailer_id})")

            # Lógica adicional: configurar scraping inicial, validar configuración, etc.

        except Exception as e:
            logger.error(f"Error in on_retailer_created handler: {e}", exc_info=True)


class NotificationHandlers:
    """Handlers para notificaciones y alertas."""

    @staticmethod
    async def on_price_changed(event: Event) -> None:
        """Handler de notificaciones para cambios de precio."""
        try:
            data = event.data
            change_percentage = data.get("change_percentage", 0)

            # Notificar cambios significativos
            if abs(change_percentage) > 20:  # Cambio mayor al 20%
                logger.warning(f"ALERT: Major price change detected: {change_percentage:.2f}%")
                # Aquí se enviarían notificaciones push, emails, etc.

        except Exception as e:
            logger.error(f"Error in price change notification handler: {e}", exc_info=True)


def register_event_handlers():
    """Registrar todos los handlers de eventos."""
    logger.info("Registering event handlers...")

    # Handlers de scraping
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, ScrapingEventHandlers.on_product_scraped)
    event_bus.subscribe(EventType.PRICE_CHANGED, ScrapingEventHandlers.on_price_changed)
    event_bus.subscribe(EventType.SCRAPING_COMPLETED, ScrapingEventHandlers.on_scraping_completed)

    # Handlers de minoristas
    event_bus.subscribe(EventType.RETAILER_CREATED, RetailerEventHandlers.on_retailer_created)

    # Handlers de notificaciones
    event_bus.subscribe(EventType.PRICE_CHANGED, NotificationHandlers.on_price_changed)

    logger.info("Event handlers registered successfully")