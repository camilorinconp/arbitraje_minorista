# backend/core/scheduler.py

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.database import SessionLocal
from ..models.minorista import Minorista
from ..services.scraper import discover_product_urls, scrape_product_data

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
    
    db = SessionLocal()
    try:
        minoristas_activos = db.query(Minorista).filter(Minorista.activo == True).all()
        logger.info(f"Encontrados {len(minoristas_activos)} minoristas activos.")
        
        if not minoristas_activos:
            logger.info("No hay minoristas activos para scrapear. Saltando ejecución.")
            return

        for minorista in minoristas_activos:
            logger.info(f"Procesando minorista: {minorista.nombre}")
            try:
                urls_a_scrapear = await discover_product_urls(minorista)
                logger.info(f"Se encontraron {len(urls_a_scrapear)} URLs para '{minorista.nombre}'.")

                for url in urls_a_scrapear:
                    try:
                        await scrape_product_data(url, minorista.id, db)
                    except Exception as e:
                        logger.error(f"Error scrapeando la URL {url} para el minorista {minorista.nombre}: {e}")
                
                # Pequeña pausa para no saturar los servidores
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error procesando al minorista {minorista.nombre}: {e}", exc_info=True)

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