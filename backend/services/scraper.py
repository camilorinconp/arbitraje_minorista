# backend/services/scraper.py

import asyncio
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import update
from datetime import datetime

from ..models.product import Product

async def scrape_product_data(product_url: str, db: Session):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Usar headless=True para producción
        page = await browser.new_page()
        
        try:
            await page.goto(product_url, wait_until='domcontentloaded')
            print(f"Navegando a: {product_url}")

            # --- Lógica de extracción de datos (ejemplo básico) ---
            # Esto es un placeholder. Deberá ser adaptado para cada minorista.
            # Para el MVP, asumimos una estructura simple.
            name_selector = 'h1'
            price_selector = '.price'
            image_selector = 'img.product-image'

            name = await page.locator(name_selector).first.text_content() if await page.locator(name_selector).first.is_visible() else "No Name"
            price_str = await page.locator(price_selector).first.text_content() if await page.locator(price_selector).first.is_visible() else "0.00"
            image_url = await page.locator(image_selector).first.get_attribute('src') if await page.locator(image_selector).first.is_visible() else None

            # Limpiar y convertir precio
            price = float(''.join(filter(str.isdigit or (lambda c: c == '.'), price_str)))

            print(f"Datos extraídos: Nombre={name}, Precio={price}, Imagen={image_url}")

            # --- Guardar o actualizar en la base de datos ---
            existing_product = db.query(Product).filter(Product.product_url == product_url).first()
            current_time = datetime.now()

            if existing_product:
                # Actualizar producto existente
                stmt = update(Product).where(Product.product_url == product_url).values(
                    name=name,
                    price=price,
                    image_url=image_url,
                    last_scraped_at=current_time
                )
                db.execute(stmt)
                db.commit()
                db.refresh(existing_product)
                print(f"Producto actualizado: {existing_product.name}")
                return existing_product
            else:
                # Crear nuevo producto
                new_product = Product(
                    name=name,
                    price=price,
                    product_url=product_url,
                    image_url=image_url,
                    last_scraped_at=current_time
                )
                db.add(new_product)
                db.commit()
                db.refresh(new_product)
                print(f"Nuevo producto añadido: {new_product.name}")
                return new_product

        except IntegrityError:
            db.rollback()
            print(f"Error de integridad al añadir/actualizar {product_url}. Posible duplicado.")
            raise HTTPException(status_code=400, detail="Product URL already exists or other integrity issue.")
        except Exception as e:
            db.rollback()
            print(f"Error durante el scraping de {product_url}: {e}")
            raise HTTPException(status_code=500, detail=f"Error scraping product: {e}")
        finally:
            await browser.close()
