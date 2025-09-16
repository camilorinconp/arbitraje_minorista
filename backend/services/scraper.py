import logging
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright, Page
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import HTTPException
import random
from typing import Callable, Any

from ..models.producto import Producto
from ..models.minorista import Minorista
from ..models.historial_precio import HistorialPrecio
from ..repositories import ProductoRepository, MinoristaRepository, HistorialPrecioRepository
from .event_bus import Event, EventType, event_bus

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


async def retry_with_exponential_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    **kwargs,
) -> Any:
    """
    Ejecuta una función con retry y backoff exponencial.

    Args:
        func: Función async a ejecutar
        max_retries: Número máximo de reintentos
        base_delay: Delay base en segundos
        max_delay: Delay máximo en segundos
        backoff_factor: Factor de multiplicación para el backoff
        jitter: Si agregar jitter aleatorio para evitar thundering herd
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    f"Función {func.__name__} falló después de {max_retries + 1} intentos. "
                    f"Último error: {str(e)}"
                )
                raise

            # Calcular delay con backoff exponencial
            delay = min(base_delay * (backoff_factor**attempt), max_delay)

            # Agregar jitter aleatorio para evitar thundering herd
            if jitter:
                delay += random.uniform(0, delay * 0.1)

            logger.warning(
                f"Intento {attempt + 1}/{max_retries + 1} de {func.__name__} falló: {str(e)}. "
                f"Reintentando en {delay:.2f} segundos..."
            )

            await asyncio.sleep(delay)

    # Esto no debería alcanzarse, pero por seguridad
    if last_exception:
        raise last_exception


async def scrape_product_from_page(
    page: Page, product_url: str, minorista: Minorista, db: AsyncSession
):
    """
    Lógica de scraping principal que opera sobre una página de Playwright ya existente.
    """
    logger.info(f"Iniciando scrape para URL: {product_url}")
    await page.goto(product_url, wait_until="domcontentloaded")

    if not all([minorista.name_selector, minorista.price_selector]):
        raise HTTPException(
            status_code=400,
            detail=f"El minorista '{minorista.nombre}' no tiene los selectores de scraping configurados.",
        )

    name_selector = minorista.name_selector
    price_selector = minorista.price_selector
    image_selector = minorista.image_selector

    name_element = page.locator(name_selector).first
    price_element = page.locator(price_selector).first

    name = (
        await name_element.text_content()
        if await name_element.is_visible()
        else "Nombre Desconocido"
    )
    price_str = (
        await price_element.text_content()
        if await price_element.is_visible()
        else "0.00"
    )

    image_url = None
    if image_selector:
        image_element = page.locator(image_selector).first
        if await image_element.is_visible():
            src = await image_element.get_attribute("src")
            if src:
                image_url = urljoin(minorista.url_base, src)

    price_limpio = "".join(
        filter(lambda x: x.isdigit() or x == ".", price_str.replace(",", "."))
    )
    price = float(price_limpio) if price_limpio else 0.00

    logger.info(f"Datos extraídos: Nombre='{name}', Precio={price}")

    # --- Guardar o actualizar en la base de datos usando repositorios ---
    producto_repo = ProductoRepository(db)
    historial_repo = HistorialPrecioRepository(db)

    # Verificar si el producto existe para detectar cambios de precio
    existing_product = await producto_repo.get_by_url_and_retailer(product_url, minorista.id)
    old_price = existing_product.price if existing_product else None
    is_new_product = existing_product is None

    # Actualizar o crear producto usando el repositorio
    producto_final = await producto_repo.update_scraped_data(
        product_url=product_url,
        id_minorista=minorista.id,
        name=name,
        price=price,
        image_url=image_url
    )

    logger.info(
        f"Producto {'actualizado' if not is_new_product else 'creado'}: "
        f"ID={producto_final.id}, Nombre='{producto_final.name}'"
    )

    # Registrar historial de precios usando el repositorio
    nuevo_historial = await historial_repo.create_price_record(
        id_producto=producto_final.id,
        id_minorista=minorista.id,
        precio=price
    )
    logger.info(f"Historial de precio registrado para producto ID={producto_final.id}")

    # Publicar evento de producto scrapeado
    scraping_event = Event(
        type=EventType.PRODUCT_SCRAPED,
        data={
            "product_id": producto_final.id,
            "retailer_id": minorista.id,
            "product_name": producto_final.name,
            "price": price,
            "old_price": old_price,
            "product_url": product_url,
            "is_new_product": is_new_product
        },
        timestamp=datetime.now(),
        source="scraper"
    )
    await event_bus.publish(scraping_event)

    return producto_final


async def _scrape_product_internal(product_url: str, id_minorista: int, db: AsyncSession):
    """
    Función interna que gestiona el ciclo de vida del navegador y llama a la lógica de scraping.
    Esta función será llamada por scrape_product_data con retry logic.
    """
    # Usar repositorio para obtener minorista
    minorista_repo = MinoristaRepository(db)
    minorista = await minorista_repo.get_by_id(id_minorista)
    if not minorista:
        raise HTTPException(
            status_code=404,
            detail=f"Minorista con ID {id_minorista} no encontrado.",
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            return await scrape_product_from_page(page, product_url, minorista, db)
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Error de integridad al procesar {product_url}: {e}")
            raise HTTPException(
                status_code=400, detail="Error de integridad de base de datos."
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Error inesperado durante el scraping de {product_url}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Error inesperado durante el scraping."
            )
        finally:
            await browser.close()


async def scrape_product_data(
    product_url: str, id_minorista: int, db: AsyncSession, max_retries: int = 3
):
    """
    Función wrapper pública que ejecuta el scraping con retry logic y backoff exponencial.

    Args:
        product_url: URL del producto a scrapear
        id_minorista: ID del minorista
        db: Sesión de base de datos
        max_retries: Número máximo de reintentos (default: 3)
    """
    return await retry_with_exponential_backoff(
        _scrape_product_internal,
        product_url,
        id_minorista,
        db,
        max_retries=max_retries,
        base_delay=1.0,
        max_delay=30.0,
        backoff_factor=2.0,
    )


async def discover_products_and_add_to_db(db_session_factory: async_sessionmaker):
    logger.info("Iniciando el proceso de descubrimiento de productos.")
    async with db_session_factory() as session:
        try:
            # Usar repositorios para operaciones de base de datos
            minorista_repo = MinoristaRepository(session)
            producto_repo = ProductoRepository(session)

            # Obtener minoristas activos con URLs de descubrimiento configuradas
            minoristas = await minorista_repo.get_retailers_with_discovery_config()

            if not minoristas:
                logger.info(
                    "No se encontraron minoristas activos con URLs de descubrimiento configuradas."
                )
                return

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                for minorista in minoristas:
                    logger.info(
                        f"Descubriendo productos para minorista: {minorista.nombre} en {minorista.discovery_url}"
                    )
                    try:
                        page = await browser.new_page()
                        await page.goto(
                            minorista.discovery_url, wait_until="domcontentloaded"
                        )

                        # Extraer enlaces de productos
                        product_links = await page.evaluate(
                            """(selector) => {
                            const links = Array.from(document.querySelectorAll(selector));
                            return links.map(link => link.href);
                        }""",
                            minorista.product_link_selector,
                        )

                        logger.info(
                            f"Se encontraron {len(product_links)} enlaces de productos para {minorista.nombre}."
                        )

                        for link in product_links:
                            # Construir URL absoluta si es relativa
                            full_url = urljoin(minorista.url_base, link)

                            # Usar repositorio para verificar si el producto existe
                            existing_product = await producto_repo.get_by_url_and_retailer(
                                full_url, minorista.id
                            )

                            if not existing_product:
                                # Crear nuevo producto usando repositorio
                                new_product = Producto(
                                    name="Producto Desconocido",  # Nombre temporal, se actualizará al raspar
                                    product_url=full_url,
                                    price=0.00,  # Precio temporal, se actualizará al raspar
                                    id_minorista=minorista.id,
                                    last_scraped_at=datetime.utcnow(),
                                )
                                await producto_repo.create(new_product)
                                logger.info(
                                    f"Nuevo producto descubierto y añadido: {full_url} para {minorista.nombre}"
                                )
                            else:
                                # Actualizar la fecha de última actualización para productos ya existentes
                                existing_product.last_scraped_at = datetime.utcnow()
                                await producto_repo.update(existing_product)
                                logger.debug(
                                    f"Producto existente actualizado: {full_url} para {minorista.nombre}"
                                )
                        await page.close()
                    except Exception as e:
                        logger.error(
                            f"Error al descubrir productos para {minorista.nombre} ({minorista.discovery_url}): {e}"
                        )
                await browser.close()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(
                f"Error de base de datos durante el descubrimiento de productos: {e}"
            )
        except Exception as e:
            logger.error(
                f"Error inesperado durante el descubrimiento de productos: {e}"
            )
    logger.info("Proceso de descubrimiento de productos finalizado.")
