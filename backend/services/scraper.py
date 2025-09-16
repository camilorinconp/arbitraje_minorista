import logging
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import HTTPException

from ..models.producto import Producto
from ..models.minorista import Minorista
from ..models.historial_precio import HistorialPrecio

# Configurar logger para este módulo
logger = logging.getLogger(__name__)





from playwright.async_api import async_playwright, Page

async def scrape_product_from_page(page: Page, product_url: str, minorista: Minorista, db: Session):
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

    name = await name_element.text_content() if await name_element.is_visible() else "Nombre Desconocido"
    price_str = await price_element.text_content() if await price_element.is_visible() else "0.00"

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

    # --- Guardar o actualizar en la base de datos ---
    current_time = datetime.now()

    producto_existente = (
        db.query(Producto)
        .filter(
            Producto.product_url == product_url,
            Producto.id_minorista == minorista.id,
        )
        .first()
    )

    if producto_existente:
        producto_existente.name = name
        producto_existente.price = price
        producto_existente.image_url = image_url
        producto_existente.last_scraped_at = current_time
        db.add(producto_existente)
        db.commit()
        db.refresh(producto_existente)
        logger.info(f"Producto actualizado: ID={producto_existente.id}, Nombre='{producto_existente.name}'")
        producto_final = producto_existente
    else:
        nuevo_producto = Producto(
            name=name,
            price=price,
            product_url=product_url,
            image_url=image_url,
            last_scraped_at=current_time,
            id_minorista=minorista.id,
            identificador_producto=None,
        )
        db.add(nuevo_producto)
        db.commit()
        db.refresh(nuevo_producto)
        logger.info(f"Nuevo producto creado: ID={nuevo_producto.id}, Nombre='{nuevo_producto.name}'")
        producto_final = nuevo_producto

    # Registrar historial de precios
    nuevo_historial = HistorialPrecio(
        id_producto=producto_final.id,
        id_minorista=minorista.id,
        precio=price,
        fecha_registro=current_time,
    )
    db.add(nuevo_historial)
    db.commit()
    db.refresh(nuevo_historial)
    logger.info(f"Historial de precio registrado para producto ID={producto_final.id}")

    return producto_final


async def scrape_product_data(product_url: str, id_minorista: int, db: Session):
    """
    Función wrapper que gestiona el ciclo de vida del navegador y llama a la lógica de scraping.
    """
    minorista = db.query(Minorista).filter(Minorista.id == id_minorista).first()
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
            db.rollback()
            logger.error(f"Error de integridad al procesar {product_url}: {e}")
            raise HTTPException(status_code=400, detail=f"Error de integridad de base de datos.")
        except Exception as e:
            db.rollback()
            logger.error(f"Error inesperado durante el scraping de {product_url}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error inesperado durante el scraping.")
        finally:
            await browser.close()


async def discover_products_and_add_to_db(db: sessionmaker):
    logger.info("Iniciando el proceso de descubrimiento de productos.")
    async with db() as session:
        try:
            # Obtener minoristas activos con URLs de descubrimiento configuradas
            stmt = select(Minorista).where(
                Minorista.activo == True,
                Minorista.discovery_url.isnot(None),
                Minorista.product_link_selector.isnot(None)
            )
            minoristas = (await session.execute(stmt)).scalars().all()

            if not minoristas:
                logger.info("No se encontraron minoristas activos con URLs de descubrimiento configuradas.")
                return

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                for minorista in minoristas:
                    logger.info(f"Descubriendo productos para minorista: {minorista.nombre} en {minorista.discovery_url}")
                    try:
                        page = await browser.new_page()
                        await page.goto(minorista.discovery_url, wait_until="domcontentloaded")

                        # Extraer enlaces de productos
                        product_links = await page.evaluate(f'''(selector) => {{
                            const links = Array.from(document.querySelectorAll(selector));
                            return links.map(link => link.href);
                        }}''', minorista.product_link_selector)

                        logger.info(f"Se encontraron {len(product_links)} enlaces de productos para {minorista.nombre}.")

                        for link in product_links:
                            # Construir URL absoluta si es relativa
                            full_url = urljoin(minorista.url_base, link)

                            existing_product = await session.execute(
                                select(Producto).where(
                                    Producto.url == full_url,
                                    Producto.minorista_id == minorista.id
                                )
                            )
                            product = existing_product.scalar_one_or_none()

                            if not product:
                                new_product = Producto(
                                    nombre="Producto Desconocido", # Nombre temporal, se actualizará al raspar
                                    url=full_url,
                                    minorista_id=minorista.id,
                                    ultima_actualizacion=datetime.utcnow(),
                                    activo=True
                                )
                                session.add(new_product)
                                logger.info(f"Nuevo producto descubierto y añadido: {full_url} para {minorista.nombre}")
                            else:
                                # Actualizar la fecha de última actualización para productos ya existentes
                                product.ultima_actualizacion = datetime.utcnow()
                                logger.debug(f"Producto existente actualizado: {full_url} para {minorista.nombre}")
                        await session.commit()
                        await page.close()
                    except Exception as e:
                        logger.error(f"Error al descubrir productos para {minorista.nombre} ({minorista.discovery_url}): {e}")
                await browser.close()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Error de base de datos durante el descubrimiento de productos: {e}")
        except Exception as e:
            logger.error(f"Error inesperado durante el descubrimiento de productos: {e}")
    logger.info("Proceso de descubrimiento de productos finalizado.")
