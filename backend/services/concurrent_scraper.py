# backend/services/concurrent_scraper.py

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext
import time

from ..models.producto import Producto
from ..repositories import ProductoRepository
from ..services.event_bus import Event, EventType, event_bus
from ..services.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ConcurrentScraper:
    """
    Scraper concurrente optimizado para procesar múltiples productos en paralelo.
    """

    def __init__(self, max_concurrent_browsers: int = 5, max_concurrent_per_browser: int = 3):
        self.max_concurrent_browsers = max_concurrent_browsers
        self.max_concurrent_per_browser = max_concurrent_per_browser
        self.browser_semaphore = asyncio.Semaphore(max_concurrent_browsers)
        self.page_semaphore = asyncio.Semaphore(max_concurrent_browsers * max_concurrent_per_browser)

    async def scrape_products_concurrently(self, products: List[Producto]) -> Dict[str, Any]:
        """
        Scrapea múltiples productos de forma concurrente.
        """
        start_time = time.time()
        results = {
            "total_products": len(products),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        if not products:
            return results

        logger.info(f"Starting concurrent scraping of {len(products)} products")

        # Publicar evento de inicio
        start_event = Event(
            type=EventType.SCRAPING_STARTED,
            data={
                "products_count": len(products),
                "concurrent_browsers": self.max_concurrent_browsers,
                "timestamp": start_time
            },
            timestamp=datetime.now(),
            source="concurrent_scraper"
        )
        await event_bus.publish(start_event)

        # Crear tasks para scraping concurrente
        semaphore = asyncio.Semaphore(self.max_concurrent_browsers * self.max_concurrent_per_browser)
        tasks = []

        for producto in products:
            task = asyncio.create_task(
                self._scrape_single_product_with_semaphore(producto, semaphore, results)
            )
            tasks.append(task)

        # Ejecutar todos los tasks concurrentemente
        await asyncio.gather(*tasks, return_exceptions=True)

        # Calcular métricas finales
        end_time = time.time()
        duration = end_time - start_time
        results["duration_seconds"] = duration
        results["products_per_second"] = len(products) / duration if duration > 0 else 0

        logger.info(
            f"Concurrent scraping completed: {results['successful']}/{results['total_products']} successful "
            f"in {duration:.2f}s ({results['products_per_second']:.2f} products/sec)"
        )

        # Publicar evento de finalización
        completion_event = Event(
            type=EventType.SCRAPING_COMPLETED,
            data=results,
            timestamp=datetime.now(),
            source="concurrent_scraper"
        )
        await event_bus.publish(completion_event)

        return results

    async def _scrape_single_product_with_semaphore(
        self, producto: Producto, semaphore: asyncio.Semaphore, results: Dict[str, Any]
    ):
        """
        Scrapea un producto individual usando semáforo para control de concurrencia.
        """
        async with semaphore:
            try:
                async with AsyncSessionLocal() as db:
                    await self._scrape_product_optimized(producto, db)
                    results["successful"] += 1
                    logger.debug(f"Successfully scraped product: {producto.name}")
            except Exception as e:
                results["failed"] += 1
                error_info = {
                    "product_id": producto.id,
                    "product_name": producto.name,
                    "error": str(e)
                }
                results["errors"].append(error_info)
                logger.error(f"Failed to scrape product {producto.name}: {e}", exc_info=True)

    async def _scrape_product_optimized(self, producto: Producto, db):
        """
        Versión optimizada del scraping individual con reutilización de browser.
        """
        from ..services.scraper import scrape_product_from_page
        from ..repositories import MinoristaRepository

        # Obtener minorista
        minorista_repo = MinoristaRepository(db)
        minorista = await minorista_repo.get_by_id(producto.id_minorista)

        if not minorista:
            raise ValueError(f"Minorista no encontrado para producto {producto.id}")

        # Usar contexto compartido de browser para mejor performance
        async with self.browser_semaphore:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--memory-pressure-off'
                    ]
                )
                try:
                    # Crear contexto optimizado
                    context = await browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        viewport={'width': 1280, 'height': 720},
                        ignore_https_errors=True
                    )

                    page = await context.new_page()

                    # Optimizaciones de página
                    await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())

                    # Ejecutar scraping
                    result = await scrape_product_from_page(page, producto.product_url, minorista, db)
                    return result

                finally:
                    await browser.close()


class BatchProcessor:
    """
    Procesador por lotes para optimizar el scraping de grandes volúmenes de productos.
    """

    def __init__(self, batch_size: int = 50, delay_between_batches: float = 2.0):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.scraper = ConcurrentScraper()

    async def process_products_in_batches(self, products: List[Producto]) -> Dict[str, Any]:
        """
        Procesa productos en lotes para evitar sobrecarga del sistema.
        """
        total_results = {
            "total_products": len(products),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "batches_processed": 0
        }

        start_time = time.time()

        # Dividir productos en lotes
        batches = [
            products[i:i + self.batch_size]
            for i in range(0, len(products), self.batch_size)
        ]

        logger.info(f"Processing {len(products)} products in {len(batches)} batches of {self.batch_size}")

        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i + 1}/{len(batches)} ({len(batch)} products)")

            try:
                batch_results = await self.scraper.scrape_products_concurrently(batch)

                # Agregar resultados del lote
                total_results["successful"] += batch_results["successful"]
                total_results["failed"] += batch_results["failed"]
                total_results["errors"].extend(batch_results["errors"])
                total_results["batches_processed"] += 1

                # Pausa entre lotes para no sobrecargar
                if i < len(batches) - 1:  # No pausar después del último lote
                    await asyncio.sleep(self.delay_between_batches)

            except Exception as e:
                logger.error(f"Error processing batch {i + 1}: {e}", exc_info=True)
                total_results["failed"] += len(batch)

        end_time = time.time()
        total_results["duration_seconds"] = end_time - start_time
        total_results["products_per_second"] = len(products) / (end_time - start_time) if end_time > start_time else 0

        logger.info(
            f"Batch processing completed: {total_results['successful']}/{total_results['total_products']} "
            f"successful in {total_results['duration_seconds']:.2f}s"
        )

        return total_results


# Instancias globales para reutilización
concurrent_scraper = ConcurrentScraper()
batch_processor = BatchProcessor()