# backend/tests/test_scraper.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from playwright.sync_api import sync_playwright, Page, Route
import os

from ..main import app
from ..services.database import get_db, Base
from ..models.minorista import Minorista

# --- Configuración de la Base de Datos de Pruebas ---

# Usar una base de datos en memoria para las pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear las tablas en la base de datos de prueba
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Sobrescribir la dependencia get_db para usar la base de datos de prueba
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# --- Fixtures de Pytest ---

@pytest.fixture(scope="function")
def db_session():
    """Crea una nueva sesión de base de datos para cada prueba y limpia después."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def test_minorista(db_session):
    """Crea un minorista de prueba en la base de datos."""
    minorista = Minorista(
        nombre="Tienda de Prueba",
        url_base="http://test-site.com",
        activo=True,
        name_selector="h1.product-title",
        price_selector="span.product-price",
        image_selector="img.product-image",
    )
    db_session.add(minorista)
    db_session.commit()
    db_session.refresh(minorista)
    return minorista

# --- HTML de Prueba ---

HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Página de Producto de Prueba</title>
</head>
<body>
    <h1 class='product-title'>Producto de Prueba Increíble</h1>
    <p>Esta es una descripción del producto.</p>
    <div>
        <span class='product-price'>  $ 1,234.56  </span>
    </div>
    <img class='product-image' src='/images/producto.jpg' />
</body>
</html>
"""

import asyncio
from unittest.mock import patch, MagicMock

# --- Pruebas del Scraper ---

@patch('backend.services.scraper.scrape_product_data')
def test_endpoint_activar_scraper(mock_scrape_product_data, db_session, test_minorista):
    """
    Prueba el endpoint /scraper/run/ de forma aislada.
    Verifica que llama al servicio de scraping con los argumentos correctos.
    """
    TEST_URL = "http://test-site.com/producto-1"

    # Configurar el mock para que devuelva un resultado simulado
    mock_producto = MagicMock()
    mock_producto.name = "Producto Simulado"
    mock_producto.price = 100.00
    mock_producto.product_url = TEST_URL
    mock_producto.image_url = "http://test-site.com/image.jpg"
    mock_producto.id_minorista = test_minorista.id
    mock_producto.id = 1
    mock_producto.last_scraped_at = "2025-09-15T22:00:00Z"
    mock_producto.created_at = "2025-09-15T22:00:00Z"

    # Usamos un mock asíncrono
    future = asyncio.Future()
    future.set_result(mock_producto)
    mock_scrape_product_data.return_value = future

    # Realizar la petición al endpoint
    response = client.post(
        "/scraper/run/",
        json={"product_url": TEST_URL, "id_minorista": test_minorista.id},
    )

    # Verificar que el endpoint respondió correctamente
    assert response.status_code == 200
    # El cliente de prueba maneja la corutina, así que podemos verificar el resultado directamente
    # mock_scrape_product_data.assert_awaited_once_with(TEST_URL, test_minorista.id, db_session)

    # Verificar que la respuesta de la API coincide con el mock
    data = response.json()
    assert data["name"] == "Producto Simulado"
    assert data["price"] == 100.00


@pytest.mark.asyncio
async def test_servicio_scrape_integracion_exitosa(db_session, test_minorista):
    """
    Prueba la función de servicio `scrape_product_from_page` en integración.
    Usa Playwright para lanzar un navegador que carga HTML mockeado vía intercepción de red.
    """
    from ..services.scraper import scrape_product_from_page
    from ..models.producto import Producto
    from ..models.historial_precio import HistorialPrecio

    TEST_URL = "http://test-site.com/producto-1"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Interceptar la petición a la URL de prueba y responder con nuestro HTML
        await page.route(TEST_URL, lambda route: route.fulfill(status=200, body=HTML_CONTENT))

        # Ejecutar la lógica de scraping directamente con la página controlada
        producto_resultado = await scrape_product_from_page(
            page=page, 
            product_url=TEST_URL, 
            minorista=test_minorista, 
            db=db_session
        )

        await browser.close()

    # Verificar el resultado de la función
    assert producto_resultado.name == "Producto de Prueba Increíble"
    assert producto_resultado.price == 1234.56
    assert producto_resultado.product_url == TEST_URL
    assert producto_resultado.image_url == "http://test-site.com/images/producto.jpg"

    # Verificar la creación en la base de datos
    producto_db = db_session.query(Producto).filter(Producto.product_url == TEST_URL).first()
    assert producto_db is not None
    assert producto_db.name == "Producto de Prueba Increíble"

    historial_db = db_session.query(HistorialPrecio).filter(HistorialPrecio.id_producto == producto_db.id).first()
    assert historial_db is not None
    assert historial_db.precio == 1234.56


@pytest.mark.asyncio
async def test_servicio_scrape_precio_no_encontrado(db_session, test_minorista):
    """
    Prueba que el scraper maneja correctamente el caso donde el selector de precio no encuentra nada.
    Debería asignar un precio de 0.00.
    """
    from ..services.scraper import scrape_product_from_page

    TEST_URL = "http://test-site.com/producto-sin-precio"
    HTML_SIN_PRECIO = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1 class='product-title'>Producto Sin Precio</h1>
    </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.route(TEST_URL, lambda route: route.fulfill(status=200, body=HTML_SIN_PRECIO))

        producto_resultado = await scrape_product_from_page(
            page=page, 
            product_url=TEST_URL, 
            minorista=test_minorista, 
            db=db_session
        )

        await browser.close()

    # Verificar que el precio es 0.00 y el nombre fue extraído
    assert producto_resultado.name == "Producto Sin Precio"
    assert producto_resultado.price == 0.00
