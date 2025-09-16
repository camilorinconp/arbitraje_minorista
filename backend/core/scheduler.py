# backend/core/scheduler.py

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.database import SessionLocal
from ..models.minorista import Minorista
from ..services.scraper import scrape_product_data, discover_products_and_add_to_db

# Configurar logger
logger = logging.getLogger(__name__)

# Crear una instancia del planificador
scheduler = AsyncIOScheduler()


async def scraping_job():
    """
    Este es el trabajo que se ejecutará periódicamente.
    Descubre y scrapea productos para todos los minoristas activos.
    """
    logger.info("Ejecutando el trabajo de scraping programado...")
    
    # Primero, ejecutar el proceso de descubrimiento de productos
    await discover_products_and_add_to_db(SessionLocal)

    db = SessionLocal()
    try:
        # Obtener todos los productos activos para scrapear
        productos_activos = db.query(Producto).filter(Producto.activo == True).all()
        logger.info(f"Encontrados {len(productos_activos)} productos activos para scrapear.")
        
        if not productos_activos:
            logger.info("No hay productos activos para scrapear. Saltando ejecución.")
            return

        for producto in productos_activos:
            logger.info(f"Scrapeando producto: {producto.nombre} ({producto.url})")
            try:
                await scrape_product_data(producto.url, producto.minorista_id, db)
                # Pequeña pausa para no saturar los servidores
                await asyncio.sleep(1) # Pausa más corta ya que es por producto
            except Exception as e:
                logger.error(f"Error scrapeando el producto {producto.nombre} (URL: {producto.url}): {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error durante la ejecución del trabajo de scraping: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Trabajo de scraping finalizado.")


async def start_scheduler():
    """
    Añade el trabajo de scraping al planificador y lo inicia.
    """
    logger.info("Iniciando el planificador de tareas...")
    
    # Ejecutar el trabajo una vez al inicio para una carga de datos inmediata.
    scheduler.add_job(scraping_job, id="initial_scraping_run", name="Scraping inicial al arrancar")
    
    # Programar el trabajo para que se ejecute periódicamente.
    scheduler.add_job(
        scraping_job, 
        trigger=IntervalTrigger(minutes=60), # Ejecutar cada 60 minutos
        id="periodic_scraping_job", 
        name="Scraping periódico de productos",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Planificador iniciado. El trabajo se ha ejecutado una vez y se repetirá cada 60 minutos.")

def stop_scheduler():
    """
    Detiene el planificador de tareas de forma segura.
    """
    if scheduler.running:
        logger.info("Deteniendo el planificador de tareas...")
        scheduler.shutdown()
        logger.info("Planificador detenido.")