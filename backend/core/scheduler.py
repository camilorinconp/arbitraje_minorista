# backend/core/scheduler.py

import logging
import asyncio
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.database import AsyncSessionLocal
from ..models.producto import Producto
from ..models.minorista import Minorista
from ..services.scraper import scrape_product_data, discover_products_and_add_to_db
from ..repositories import ProductoRepository
from ..services.event_bus import Event, EventType, event_bus
from ..services.concurrent_scraper import batch_processor
from sqlalchemy.future import select

# Configurar logger
logger = logging.getLogger(__name__)

# Crear una instancia del planificador
scheduler = AsyncIOScheduler()


async def scraping_job():
    """
    Este es el trabajo que se ejecutará periódicamente.
    Descubre y scrapea productos para todos los minoristas activos.
    """
    start_time = time.time()
    products_processed = 0
    errors_count = 0

    logger.info("Ejecutando el trabajo de scraping programado...")

    # Publicar evento de inicio de scraping
    start_event = Event(
        type=EventType.SCRAPING_STARTED,
        data={"timestamp": start_time},
        timestamp=datetime.now(),
        source="scheduler"
    )
    await event_bus.publish(start_event)

    try:
        # Primero, ejecutar el proceso de descubrimiento de productos
        await discover_products_and_add_to_db(AsyncSessionLocal)

        async with AsyncSessionLocal() as db:
            try:
                # Usar repositorio para obtener productos de minoristas activos
                producto_repo = ProductoRepository(db)
                productos_activos = await producto_repo.get_products_from_active_retailers()

                logger.info(
                    f"Encontrados {len(productos_activos)} productos de minoristas activos para scrapear."
                )

                if not productos_activos:
                    logger.info("No hay productos de minoristas activos para scrapear. Saltando ejecución.")
                    return

                # Usar scraper concurrente para mejor performance
                logger.info(f"Iniciando scraping concurrente de {len(productos_activos)} productos")
                scraping_results = await batch_processor.process_products_in_batches(productos_activos)

                products_processed = scraping_results["successful"]
                errors_count = scraping_results["failed"]

                logger.info(
                    f"Scraping concurrente completado: {products_processed} exitosos, "
                    f"{errors_count} fallos en {scraping_results.get('duration_seconds', 0):.2f}s"
                )

            except Exception as e:
                logger.error(
                    f"Error durante la ejecución del trabajo de scraping: {e}", exc_info=True
                )
            finally:
                logger.info("Trabajo de scraping finalizado.")

    finally:
        # Publicar evento de finalización de scraping
        end_time = time.time()
        duration = end_time - start_time

        completion_event = Event(
            type=EventType.SCRAPING_COMPLETED,
            data={
                "duration_seconds": duration,
                "products_processed": products_processed,
                "errors_count": errors_count,
                "success_rate": ((products_processed - errors_count) / products_processed * 100) if products_processed > 0 else 0
            },
            timestamp=datetime.now(),
            source="scheduler"
        )
        await event_bus.publish(completion_event)


async def start_scheduler():
    """
    Añade el trabajo de scraping al planificador y lo inicia.
    """
    logger.info("Iniciando el planificador de tareas...")

    # Ejecutar el trabajo una vez al inicio para una carga de datos inmediata.
    scheduler.add_job(
        scraping_job, id="initial_scraping_run", name="Scraping inicial al arrancar"
    )

    # Programar el trabajo para que se ejecute periódicamente.
    scheduler.add_job(
        scraping_job,
        trigger=IntervalTrigger(minutes=60),  # Ejecutar cada 60 minutos
        id="periodic_scraping_job",
        name="Scraping periódico de productos",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Planificador iniciado. El trabajo se ha ejecutado una vez y se repetirá cada 60 minutos."
    )


def stop_scheduler():
    """
    Detiene el planificador de tareas de forma segura.
    """
    if scheduler.running:
        logger.info("Deteniendo el planificador de tareas...")
        scheduler.shutdown()
        logger.info("Planificador detenido.")
