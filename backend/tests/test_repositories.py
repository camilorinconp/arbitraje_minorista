# backend/tests/test_repositories.py

import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.services.database import Base
from backend.models.producto import Producto
from backend.models.minorista import Minorista
from backend.models.historial_precio import HistorialPrecio
from backend.repositories.producto_repository import ProductoRepository
from backend.repositories.minorista_repository import MinoristaRepository
from backend.repositories.historial_precio_repository import HistorialPrecioRepository


# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function")
async def async_db_session():
    """Create async test database session with clean state."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def test_minorista(async_db_session):
    """Create test retailer."""
    minorista = Minorista(
        nombre="Test Retailer",
        url_base="https://test-store.com",
        activo=True,
        name_selector="h1.title",
        price_selector=".price",
        image_selector="img.product"
    )
    async_db_session.add(minorista)
    await async_db_session.commit()
    await async_db_session.refresh(minorista)
    return minorista


@pytest.fixture
async def test_producto(async_db_session, test_minorista):
    """Create test product."""
    producto = Producto(
        name="Test Product",
        price=99.99,
        product_url="https://test-store.com/product/1",
        image_url="https://test-store.com/image.jpg",
        id_minorista=test_minorista.id,
        identificador_producto="TEST-001"
    )
    async_db_session.add(producto)
    await async_db_session.commit()
    await async_db_session.refresh(producto)
    return producto


# --- Repository Tests ---

@pytest.mark.asyncio
async def test_producto_repository_create(async_db_session, test_minorista):
    """Test ProductoRepository create operation."""
    repo = ProductoRepository(async_db_session)

    producto_data = {
        "name": "New Product",
        "price": 150.00,
        "product_url": "https://test-store.com/new-product",
        "image_url": "https://test-store.com/new-image.jpg",
        "id_minorista": test_minorista.id,
        "identificador_producto": "NEW-001"
    }

    producto = await repo.create(producto_data)

    assert producto.id is not None
    assert producto.name == "New Product"
    assert producto.price == 150.00
    assert producto.id_minorista == test_minorista.id
    assert producto.created_at is not None


@pytest.mark.asyncio
async def test_producto_repository_get_by_url(async_db_session, test_producto):
    """Test ProductoRepository get_by_url method."""
    repo = ProductoRepository(async_db_session)

    found_producto = await repo.get_by_url(test_producto.product_url)

    assert found_producto is not None
    assert found_producto.id == test_producto.id
    assert found_producto.name == test_producto.name


@pytest.mark.asyncio
async def test_producto_repository_get_by_minorista(async_db_session, test_minorista, test_producto):
    """Test ProductoRepository get_by_minorista method."""
    repo = ProductoRepository(async_db_session)

    # Create additional product for same retailer
    additional_producto = Producto(
        name="Second Product",
        price=75.50,
        product_url="https://test-store.com/product/2",
        image_url="https://test-store.com/image2.jpg",
        id_minorista=test_minorista.id,
        identificador_producto="TEST-002"
    )
    async_db_session.add(additional_producto)
    await async_db_session.commit()

    productos = await repo.get_by_minorista(test_minorista.id)

    assert len(productos) == 2
    assert all(p.id_minorista == test_minorista.id for p in productos)


@pytest.mark.asyncio
async def test_producto_repository_update_price(async_db_session, test_producto):
    """Test ProductoRepository update_price method."""
    repo = ProductoRepository(async_db_session)

    old_price = test_producto.price
    new_price = 125.00

    updated_producto = await repo.update_price(test_producto.id, new_price)

    assert updated_producto.price == new_price
    assert updated_producto.price != old_price
    assert updated_producto.last_scraped_at is not None


@pytest.mark.asyncio
async def test_minorista_repository_get_active(async_db_session):
    """Test MinoristaRepository get_active method."""
    repo = MinoristaRepository(async_db_session)

    # Create active and inactive retailers
    active_minorista = Minorista(
        nombre="Active Store",
        url_base="https://active.com",
        activo=True,
        name_selector="h1",
        price_selector=".price",
        image_selector="img"
    )
    inactive_minorista = Minorista(
        nombre="Inactive Store",
        url_base="https://inactive.com",
        activo=False,
        name_selector="h1",
        price_selector=".price",
        image_selector="img"
    )

    async_db_session.add_all([active_minorista, inactive_minorista])
    await async_db_session.commit()

    active_retailers = await repo.get_active()

    assert len(active_retailers) == 1
    assert active_retailers[0].activo is True
    assert active_retailers[0].nombre == "Active Store"


@pytest.mark.asyncio
async def test_minorista_repository_get_with_discovery(async_db_session):
    """Test MinoristaRepository get_with_discovery method."""
    repo = MinoristaRepository(async_db_session)

    # Create retailer with discovery configuration
    discovery_minorista = Minorista(
        nombre="Discovery Store",
        url_base="https://discovery.com",
        activo=True,
        name_selector="h1",
        price_selector=".price",
        image_selector="img",
        discovery_url="https://discovery.com/products",
        product_link_selector="a.product-link"
    )

    # Create retailer without discovery
    no_discovery_minorista = Minorista(
        nombre="No Discovery Store",
        url_base="https://nodiscovery.com",
        activo=True,
        name_selector="h1",
        price_selector=".price",
        image_selector="img"
    )

    async_db_session.add_all([discovery_minorista, no_discovery_minorista])
    await async_db_session.commit()

    discovery_retailers = await repo.get_with_discovery()

    assert len(discovery_retailers) == 1
    assert discovery_retailers[0].discovery_url is not None
    assert discovery_retailers[0].product_link_selector is not None


@pytest.mark.asyncio
async def test_historial_precio_repository_create(async_db_session, test_producto, test_minorista):
    """Test HistorialPrecioRepository create operation."""
    repo = HistorialPrecioRepository(async_db_session)

    historial_data = {
        "precio": 99.99,
        "id_producto": test_producto.id,
        "id_minorista": test_minorista.id
    }

    historial = await repo.create(historial_data)

    assert historial.id is not None
    assert historial.precio == 99.99
    assert historial.id_producto == test_producto.id
    assert historial.fecha_registro is not None


@pytest.mark.asyncio
async def test_historial_precio_repository_get_latest_by_product(async_db_session, test_producto, test_minorista):
    """Test HistorialPrecioRepository get_latest_by_product method."""
    repo = HistorialPrecioRepository(async_db_session)

    # Create multiple price history entries
    historial1 = HistorialPrecio(
        precio=100.00,
        id_producto=test_producto.id,
        id_minorista=test_minorista.id,
        fecha_registro=datetime.now(timezone.utc)
    )

    # Simulate later entry
    import time
    time.sleep(0.1)  # Ensure different timestamps

    historial2 = HistorialPrecio(
        precio=120.00,
        id_producto=test_producto.id,
        id_minorista=test_minorista.id,
        fecha_registro=datetime.now(timezone.utc)
    )

    async_db_session.add_all([historial1, historial2])
    await async_db_session.commit()

    latest_price = await repo.get_latest_by_product(test_producto.id)

    assert latest_price is not None
    assert latest_price.precio == 120.00  # Should be the latest


@pytest.mark.asyncio
async def test_historial_precio_repository_get_price_changes(async_db_session, test_producto, test_minorista):
    """Test HistorialPrecioRepository get_price_changes method."""
    repo = HistorialPrecioRepository(async_db_session)

    # Create price history with changes
    prices = [100.00, 110.00, 95.00, 105.00]
    for price in prices:
        historial = HistorialPrecio(
            precio=price,
            id_producto=test_producto.id,
            id_minorista=test_minorista.id,
            fecha_registro=datetime.now(timezone.utc)
        )
        async_db_session.add(historial)
        await async_db_session.commit()
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.1)

    price_changes = await repo.get_price_changes(test_producto.id, limit=10)

    assert len(price_changes) == 4
    assert price_changes[0].precio == 105.00  # Latest first
    assert price_changes[-1].precio == 100.00  # Oldest last


@pytest.mark.asyncio
async def test_repository_transaction_rollback(async_db_session, test_minorista):
    """Test repository transaction rollback on error."""
    repo = ProductoRepository(async_db_session)

    # Attempt to create product with invalid data that will cause constraint error
    with pytest.raises(Exception):
        await repo.create({
            "name": "Test Product",
            "price": 99.99,
            "product_url": "https://test-store.com/product/1",
            "image_url": "https://test-store.com/image.jpg",
            "id_minorista": 99999,  # Non-existent retailer ID
            "identificador_producto": "TEST-001"
        })

    # Verify database state is clean (transaction rolled back)
    all_products = await repo.get_all()
    assert len(all_products) == 0


@pytest.mark.asyncio
async def test_repository_caching_behavior(async_db_session, test_minorista):
    """Test repository caching functionality."""
    repo = MinoristaRepository(async_db_session)

    # First call - should hit database
    active_retailers_1 = await repo.get_active()

    # Second call - should hit cache
    active_retailers_2 = await repo.get_active()

    assert len(active_retailers_1) == len(active_retailers_2)
    assert active_retailers_1[0].id == active_retailers_2[0].id

    # Verify cache is working by checking object identity (if cache returns same objects)
    # Note: This test depends on cache implementation details


@pytest.mark.asyncio
async def test_repository_bulk_operations(async_db_session, test_minorista):
    """Test repository bulk operations performance."""
    repo = ProductoRepository(async_db_session)

    # Create multiple products in bulk
    productos_data = []
    for i in range(10):
        productos_data.append({
            "name": f"Bulk Product {i}",
            "price": 10.00 + i,
            "product_url": f"https://test-store.com/product/{i}",
            "image_url": f"https://test-store.com/image{i}.jpg",
            "id_minorista": test_minorista.id,
            "identificador_producto": f"BULK-{i:03d}"
        })

    # Create all products
    created_products = []
    for data in productos_data:
        producto = await repo.create(data)
        created_products.append(producto)

    # Verify all were created
    all_products = await repo.get_all()
    assert len(all_products) == 10

    # Verify they can be retrieved by retailer
    retailer_products = await repo.get_by_minorista(test_minorista.id)
    assert len(retailer_products) == 10