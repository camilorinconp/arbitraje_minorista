# backend/services/scraper.py

import logging
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import HTTPException

from ..models.producto import Producto
from ..models.minorista import Minorista
from ..models.historial_precio import HistorialPrecio

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


async def scrape_product_data(product_url: str, id_minorista: int, db: Session):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )  # Usar headless=True para producción
        page = await browser.new_page()

        try:
            logger.info(f"Iniciando scrape para URL: {product_url}")
            await page.goto(product_url, wait_until="domcontentloaded")

            # --- Lógica de extracción de datos dinámica ---
            minorista = db.query(Minorista).filter(Minorista.id == id_minorista).first()
            if not minorista:
                raise HTTPException(
                    status_code=404,
                    detail=f"Minorista con ID {id_minorista} no encontrado.",
                )

            if not all([minorista.name_selector, minorista.price_selector]):
                raise HTTPException(
                    status_code=400,
                    detail=f"El minorista '{minorista.nombre}' no tiene los selectores de scraping configurados.",
                )

            name_selector = minorista.name_selector
            price_selector = minorista.price_selector
            image_selector = minorista.image_selector

            name = (
                await page.locator(name_selector).first.text_content()
                if await page.locator(name_selector).first.is_visible()
                else "Nombre Desconocido"
            )
            price_str = (
                await page.locator(price_selector).first.text_content()
                if await page.locator(price_selector).first.is_visible()
                else "0.00"
            )

            image_url = None
            if image_selector and await page.locator(image_selector).first.is_visible():
                image_url = await page.locator(image_selector).first.get_attribute("src")

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
                    Producto.id_minorista == id_minorista,
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
            else:
                nuevo_producto = Producto(
                    name=name,
                    price=price,
                    product_url=product_url,
                    image_url=image_url,
                    last_scraped_at=current_time,
                    id_minorista=id_minorista,
                    identificador_producto=None,
                )
                db.add(nuevo_producto)
                db.commit()
                db.refresh(nuevo_producto)
                logger.info(f"Nuevo producto creado: ID={nuevo_producto.id}, Nombre='{nuevo_producto.name}'")
                producto_existente = nuevo_producto

            # Registrar historial de precios
            nuevo_historial = HistorialPrecio(
                id_producto=producto_existente.id,
                id_minorista=id_minorista,
                precio=price,
                fecha_registro=current_time,
            )
            db.add(nuevo_historial)
            db.commit()
            db.refresh(nuevo_historial)
            logger.info(f"Historial de precio registrado para producto ID={producto_existente.id}")

            return producto_existente

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
