# backend/services/scraper.py

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from fastapi import HTTPException

from ..models.producto import Producto
from ..models.minorista import Minorista
from ..models.historial_precio import HistorialPrecio


async def scrape_product_data(product_url: str, id_minorista: int, db: Session):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True
        )  # Usar headless=True para producción
        page = await browser.new_page()

        try:
            await page.goto(product_url, wait_until="domcontentloaded")
            print(f"Navegando a: {product_url}")

            # --- Lógica de extracción de datos dinámica ---

            # Buscar el minorista para obtener los selectores
            minorista = db.query(Minorista).filter(Minorista.id == id_minorista).first()
            if not minorista:
                raise HTTPException(
                    status_code=404,
                    detail=f"Minorista con ID {id_minorista} no encontrado.",
                )

            # Validar que los selectores estén configurados
            if not all([minorista.name_selector, minorista.price_selector]):
                raise HTTPException(
                    status_code=400,
                    detail=f"El minorista '{minorista.nombre}' no tiene los selectores de scraping configurados.",
                )

            name_selector = minorista.name_selector
            price_selector = minorista.price_selector
            image_selector = minorista.image_selector  # Puede ser nulo

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
                image_url = await page.locator(image_selector).first.get_attribute(
                    "src"
                )

            # Limpiar y convertir price
            # Asumiendo que el price puede venir con símbolos de moneda o comas
            price_limpio = "".join(
                filter(lambda x: x.isdigit() or x == ".", price_str.replace(",", "."))
            )
            price = float(price_limpio) if price_limpio else 0.00

            print(f"Datos extraídos: Nombre={name}, Precio={price}, Imagen={image_url}")

            # --- Guardar o actualizar en la base de datos ---
            current_time = datetime.now()

            # Buscar producto existente por URL y minorista
            producto_existente = (
                db.query(Producto)
                .filter(
                    Producto.product_url == product_url,
                    Producto.id_minorista == id_minorista,
                )
                .first()
            )

            if producto_existente:
                # Actualizar producto existente
                producto_existente.name = name
                producto_existente.price = price
                producto_existente.image_url = image_url
                producto_existente.last_scraped_at = current_time
                # identificador_producto no se actualiza aquí, se asume que es estático
                db.add(producto_existente)  # add para marcar como modificado
                db.commit()
                db.refresh(producto_existente)
                print(f"Producto actualizado: {producto_existente.name}")
            else:
                # Crear nuevo producto
                nuevo_producto = Producto(
                    name=name,
                    precio=price,
                    product_url=product_url,
                    image_url=image_url,
                    last_scraped_at=current_time,
                    id_minorista=id_minorista,
                    identificador_producto=None,  # Placeholder, se puede extraer después
                )
                db.add(nuevo_producto)
                db.commit()
                db.refresh(nuevo_producto)
                print(f"Nuevo producto añadido: {nuevo_producto.name}")
                producto_existente = nuevo_producto

            # Registrar historial de precioss
            nuevo_historial = HistorialPrecio(
                id_producto=producto_existente.id,
                id_minorista=id_minorista,
                precio=price,
                fecha_registro=current_time,
            )
            db.add(nuevo_historial)
            db.commit()
            db.refresh(nuevo_historial)
            print(f"Historial de precio registrado para {producto_existente.name}")

            return producto_existente

        except IntegrityError as e:
            db.rollback()
            print(f"Error de integridad al añadir/actualizar {product_url}: {e}")
            raise HTTPException(status_code=400, detail=f"Error de integridad: {e}")
        except Exception as e:
            db.rollback()
            print(f"Error durante el scraping de {product_url}: {e}")
            raise HTTPException(status_code=500, detail=f"Error scraping product: {e}")
        finally:
            await browser.close()
