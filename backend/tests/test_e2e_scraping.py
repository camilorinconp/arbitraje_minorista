# backend/tests/test_e2e_scraping.py

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
import json

import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from main import app
from services.database import get_db, Base
from models.minorista import Minorista
from models.producto import Producto
from models.historial_precio import HistorialPrecio


# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_e2e.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database session for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_minorista(db_session):
    """Create test retailer with proper scraping configuration."""
    minorista = Minorista(
        nombre="Test E-commerce Store",
        url_base="https://test-store.com",
        activo=True,
        name_selector="h1.product-title",
        price_selector=".price-current",
        image_selector="img.product-image",
        # Discovery configuration
        discovery_url="https://test-store.com/products",
        product_link_selector="a.product-link"
    )
    db_session.add(minorista)
    db_session.commit()
    db_session.refresh(minorista)
    return minorista


# --- End-to-End Test Scenarios ---

def test_e2e_complete_scraping_workflow(db_session, test_minorista):
    """
    Test complete scraping workflow:
    1. Create retailer
    2. Trigger scraping
    3. Verify product creation
    4. Verify price history
    5. Check metrics
    """

    # Mock HTML content for scraping
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Product Page</title></head>
    <body>
        <h1 class="product-title">Premium Test Product</h1>
        <div class="price-current">$299.99</div>
        <img class="product-image" src="/images/test-product.jpg" alt="Test Product" />
    </body>
    </html>
    """

    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        # Setup Playwright mock
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.goto = MagicMock()
        mock_page.wait_for_load_state = MagicMock()
        mock_page.content.return_value = mock_html
        mock_page.query_selector.side_effect = lambda selector: {
            'h1.product-title': MagicMock(text_content=lambda: "Premium Test Product"),
            '.price-current': MagicMock(text_content=lambda: "$299.99"),
            'img.product-image': MagicMock(get_attribute=lambda attr: "/images/test-product.jpg" if attr == "src" else None)
        }.get(selector)

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        # Step 1: Trigger scraping via API
        scrape_request = {
            "product_url": "https://test-store.com/product/test-item",
            "id_minorista": test_minorista.id
        }

        response = client.post("/scraper/run/", json=scrape_request)

        # Verify scraping response
        assert response.status_code == 200
        product_data = response.json()

        assert product_data["name"] == "Premium Test Product"
        assert product_data["price"] == 299.99
        assert product_data["product_url"] == "https://test-store.com/product/test-item"
        assert product_data["id_minorista"] == test_minorista.id

        # Step 2: Verify product was created in database
        created_product = db_session.query(Producto).filter(
            Producto.product_url == "https://test-store.com/product/test-item"
        ).first()

        assert created_product is not None
        assert created_product.name == "Premium Test Product"
        assert created_product.price == 299.99
        assert created_product.id_minorista == test_minorista.id

        # Step 3: Verify price history was recorded
        price_history = db_session.query(HistorialPrecio).filter(
            HistorialPrecio.id_producto == created_product.id
        ).all()

        assert len(price_history) == 1
        assert price_history[0].precio == 299.99
        assert price_history[0].id_minorista == test_minorista.id

        # Step 4: Test product update scenario
        # Mock updated content with new price
        updated_html = mock_html.replace("$299.99", "$249.99")
        mock_page.content.return_value = updated_html
        mock_page.query_selector.side_effect = lambda selector: {
            'h1.product-title': MagicMock(text_content=lambda: "Premium Test Product"),
            '.price-current': MagicMock(text_content=lambda: "$249.99"),
            'img.product-image': MagicMock(get_attribute=lambda attr: "/images/test-product.jpg" if attr == "src" else None)
        }.get(selector)

        # Trigger scraping again for same product
        response = client.post("/scraper/run/", json=scrape_request)
        assert response.status_code == 200

        updated_product_data = response.json()
        assert updated_product_data["price"] == 249.99

        # Verify price history now has 2 entries
        updated_price_history = db_session.query(HistorialPrecio).filter(
            HistorialPrecio.id_producto == created_product.id
        ).order_by(HistorialPrecio.fecha_registro.desc()).all()

        assert len(updated_price_history) == 2
        assert updated_price_history[0].precio == 249.99  # Latest
        assert updated_price_history[1].precio == 299.99  # Previous


def test_e2e_scraping_error_handling(db_session, test_minorista):
    """
    Test scraping error handling:
    1. Network timeout
    2. Invalid selectors
    3. Missing elements
    """

    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        # Test 1: Network timeout
        mock_playwright.side_effect = asyncio.TimeoutError("Page load timeout")

        scrape_request = {
            "product_url": "https://test-store.com/timeout-product",
            "id_minorista": test_minorista.id
        }

        response = client.post("/scraper/run/", json=scrape_request)

        # Should handle timeout gracefully
        assert response.status_code in [400, 500]  # Error response

        # Test 2: Invalid HTML/Missing elements
        mock_playwright.side_effect = None
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body>No product info</body></html>"
        mock_page.query_selector.return_value = None  # No elements found

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        response = client.post("/scraper/run/", json=scrape_request)

        # Should handle missing elements
        assert response.status_code in [200, 400]  # May create product with default values


def test_e2e_rate_limiting_integration(db_session, test_minorista):
    """
    Test rate limiting integration in scraping endpoints.
    """

    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        # Setup basic mock
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body><h1 class='product-title'>Test</h1></body></html>"
        mock_page.query_selector.side_effect = lambda selector: MagicMock(text_content=lambda: "Test") if 'title' in selector else None

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        scrape_request = {
            "product_url": "https://test-store.com/rate-limit-test",
            "id_minorista": test_minorista.id
        }

        # Make multiple rapid requests to test rate limiting
        responses = []
        for i in range(15):  # Exceed the 10/minute limit
            response = client.post("/scraper/run/", json=scrape_request)
            responses.append(response.status_code)

        # Should see some 429 (Too Many Requests) responses
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)

        # At least some requests should be rate limited
        assert rate_limited_count > 0, "Rate limiting should have kicked in"
        assert success_count <= 10, "Should not exceed rate limit"


def test_e2e_data_management_integration(db_session, test_minorista):
    """
    Test complete data management workflow:
    1. Create retailer via API
    2. Update retailer configuration
    3. Scrape products
    4. Query products
    5. View price history
    """

    # Step 1: Create new retailer via API
    new_retailer_data = {
        "nombre": "API Created Store",
        "url_base": "https://api-store.com",
        "activo": True,
        "name_selector": "h2.title",
        "price_selector": ".cost",
        "image_selector": "img.main"
    }

    response = client.post("/gestion-datos/minoristas/", json=new_retailer_data)
    assert response.status_code == 201

    created_retailer = response.json()
    retailer_id = created_retailer["id"]

    # Step 2: Update retailer configuration
    update_data = {
        **new_retailer_data,
        "discovery_url": "https://api-store.com/catalog",
        "product_link_selector": "a.item-link"
    }

    response = client.put(f"/gestion-datos/minoristas/{retailer_id}", json=update_data)
    assert response.status_code == 200

    # Step 3: Scrape products with updated retailer
    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = """
        <html><body>
            <h2 class="title">API Test Product</h2>
            <div class="cost">$199.99</div>
            <img class="main" src="/api-product.jpg" />
        </body></html>
        """
        mock_page.query_selector.side_effect = lambda selector: {
            'h2.title': MagicMock(text_content=lambda: "API Test Product"),
            '.cost': MagicMock(text_content=lambda: "$199.99"),
            'img.main': MagicMock(get_attribute=lambda attr: "/api-product.jpg" if attr == "src" else None)
        }.get(selector)

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        scrape_request = {
            "product_url": "https://api-store.com/product/api-test",
            "id_minorista": retailer_id
        }

        response = client.post("/scraper/run/", json=scrape_request)
        assert response.status_code == 200

    # Step 4: Query products via API
    response = client.get("/gestion-datos/productos/")
    assert response.status_code == 200

    products = response.json()
    api_products = [p for p in products if p["id_minorista"] == retailer_id]
    assert len(api_products) == 1
    assert api_products[0]["name"] == "API Test Product"

    # Step 5: Check specific product details
    product_id = api_products[0]["id"]
    response = client.get(f"/gestion-datos/productos/{product_id}")
    assert response.status_code == 200

    product_detail = response.json()
    assert product_detail["price"] == 199.99


def test_e2e_observability_integration(db_session, test_minorista):
    """
    Test observability integration during scraping operations.
    """

    # Check initial health status
    response = client.get("/observability/health")
    assert response.status_code in [200, 503]  # Healthy or unhealthy but responsive

    health_data = response.json()
    assert "status" in health_data
    assert "checks" in health_data

    # Check metrics endpoint
    response = client.get("/observability/metrics")
    assert response.status_code == 200

    metrics_data = response.json()
    assert "metrics" in metrics_data

    # Perform scraping operation and check metrics update
    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body><h1 class='product-title'>Metrics Test</h1></body></html>"
        mock_page.query_selector.side_effect = lambda selector: MagicMock(text_content=lambda: "Metrics Test") if 'title' in selector else None

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        scrape_request = {
            "product_url": "https://test-store.com/metrics-test",
            "id_minorista": test_minorista.id
        }

        # Perform scraping
        response = client.post("/scraper/run/", json=scrape_request)
        assert response.status_code == 200

    # Check metrics after scraping
    response = client.get("/observability/metrics")
    assert response.status_code == 200

    updated_metrics = response.json()
    assert "metrics" in updated_metrics

    # Check rate limit status
    response = client.get("/rate-limit/status")
    assert response.status_code == 200

    rate_limit_status = response.json()
    assert "client_id" in rate_limit_status
    assert "limits" in rate_limit_status


def test_e2e_error_recovery_and_resilience(db_session, test_minorista):
    """
    Test system resilience and error recovery mechanisms.
    """

    # Test 1: Scraping with invalid retailer ID
    invalid_scrape_request = {
        "product_url": "https://test-store.com/invalid-retailer",
        "id_minorista": 99999  # Non-existent retailer
    }

    response = client.post("/scraper/run/", json=invalid_scrape_request)
    assert response.status_code in [400, 404]  # Should handle gracefully

    # Test 2: Invalid product URL format
    invalid_url_request = {
        "product_url": "not-a-valid-url",
        "id_minorista": test_minorista.id
    }

    response = client.post("/scraper/run/", json=invalid_url_request)
    assert response.status_code == 422  # Validation error

    # Test 3: Test system continues working after errors
    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body><h1 class='product-title'>Recovery Test</h1></body></html>"
        mock_page.query_selector.side_effect = lambda selector: MagicMock(text_content=lambda: "Recovery Test") if 'title' in selector else None

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        valid_request = {
            "product_url": "https://test-store.com/recovery-test",
            "id_minorista": test_minorista.id
        }

        response = client.post("/scraper/run/", json=valid_request)
        assert response.status_code == 200  # System recovered and works

    # Test 4: Health checks still work after errors
    response = client.get("/observability/health")
    assert response.status_code in [200, 503]  # System responsive


# --- Performance Tests ---

def test_e2e_concurrent_scraping_performance(db_session, test_minorista):
    """
    Test concurrent scraping performance and system stability.
    """

    with patch('backend.services.scraper.async_playwright') as mock_playwright:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body><h1 class='product-title'>Concurrent Test</h1></body></html>"
        mock_page.query_selector.side_effect = lambda selector: MagicMock(text_content=lambda: f"Concurrent Test {hash(selector) % 100}") if 'title' in selector else None

        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        # Create multiple scraping requests
        scrape_requests = [
            {
                "product_url": f"https://test-store.com/concurrent-{i}",
                "id_minorista": test_minorista.id
            }
            for i in range(5)  # 5 concurrent requests
        ]

        import time
        start_time = time.time()

        # Execute requests (simulating concurrent behavior)
        responses = []
        for request in scrape_requests:
            response = client.post("/scraper/run/", json=request)
            responses.append(response.status_code)

        end_time = time.time()
        duration = end_time - start_time

        # All requests should complete successfully (or be rate limited)
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)

        assert success_count + rate_limited_count == 5
        assert duration < 30  # Should complete within 30 seconds

        # Verify system is still responsive
        response = client.get("/observability/health")
        assert response.status_code in [200, 503]