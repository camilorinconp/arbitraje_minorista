# backend/core/scheduler.py

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.database import SessionLocal
from ..models.minorista import Minorista

# Configurar logger
logger = logging.getLogger(__name__)

# Crear una instancia del planificador
scheduler = AsyncIOScheduler()


def scraping_job():
    """
    Este es el trabajo que se ejecutará periódicamente.
    La lógica para encontrar y scrapear productos irá aquí.
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
            # TODO: Implementar la lógica de descubrimiento y scraping para cada minorista.

    except Exception as e:
        logger.error(f"Error durante la ejecución del trabajo de scraping: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Trabajo de scraping finalizado.")


def start_scheduler():
    """
    Añade el trabajo de scraping al planificador y lo inicia.
    """
    logger.info("Iniciando el planificador de tareas...")
    # Correr el job una vez al iniciar para pruebas rápidas
    scheduler.add_job(scraping_job, id="initial_run") 
    
    scheduler.add_job(
        scraping_job, 
        trigger=IntervalTrigger(minutes=60), # Ejecutar cada 60 minutos
        id="scraping_job", 
        name="Scraping periódico de productos",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Planificador iniciado. El trabajo de scraping se ejecutará al inicio y luego cada 60 minutos.")

def stop_scheduler():
    """
    Detiene el planificador de tareas de forma segura.
    """
    if scheduler.running:
        logger.info("Deteniendo el planificador de tareas...")
        scheduler.shutdown()
        logger.info("Planificador detenido.") planificador y lo inicia.
    """
    logger.info("Iniciando el planificador de tareas...")
    scheduler.add_job(
        scraping_job, 
        trigger=IntervalTrigger(minutes=60), # Ejecutar cada 60 minutos
        id="scraping_job", 
        name="Scraping periódico de productos",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Planificador iniciado. El trabajo de scraping se ejecutará cada 60 minutos.")

def stop_scheduler():
    """
    Detiene el planificador de tareas de forma segura.
    """
    if scheduler.running:
        logger.info("Deteniendo el planificador de tareas...")
        scheduler.shutdown()
        logger.info("Planificador detenido.")