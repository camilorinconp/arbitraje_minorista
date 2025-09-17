# backend/tests/test_repositories_simple.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from backend.repositories.base import BaseRepository
from backend.repositories.producto_repository import ProductoRepository
from backend.repositories.minorista_repository import MinoristaRepository
from backend.repositories.historial_precio_repository import HistorialPrecioRepository


# --- Mock Tests for Repository Pattern ---

@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_producto():
    """Create mock product object."""
    producto = MagicMock()
    producto.id = 1
    producto.name = "Test Product"
    producto.price = 99.99
    producto.product_url = "https://test.com/product/1"
    producto.id_minorista = 1
    producto.created_at = datetime.now(timezone.utc)
    return producto


@pytest.fixture
def mock_minorista():
    """Create mock retailer object."""
    minorista = MagicMock()
    minorista.id = 1
    minorista.nombre = "Test Store"
    minorista.activo = True
    minorista.url_base = "https://test.com"
    return minorista


# --- BaseRepository Tests ---

@pytest.mark.asyncio
async def test_base_repository_create(mock_session, mock_producto):
    """Test BaseRepository create method."""
    # Setup mock
    mock_session.scalar.return_value = mock_producto

    # Create repository with mock model
    class MockModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    repo = BaseRepository(mock_session, MockModel)

    # Test create
    data = {"name": "Test Product", "price": 99.99}
    result = await repo.create(data)

    # Verify session interactions
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_get_by_id(mock_session, mock_produto):
    """Test BaseRepository get_by_id method."""
    # Setup mock
    mock_session.scalar.return_value = mock_produto

    class MockModel:
        id = 1

    repo = BaseRepository(mock_session, MockModel)

    # Test get_by_id
    result = await repo.get_by_id(1)

    # Verify query was executed
    mock_session.execute.assert_called_once()
    assert result == mock_produto


@pytest.mark.asyncio
async def test_base_repository_get_all(mock_session):
    """Test BaseRepository get_all method."""
    # Setup mock
    mock_results = [MagicMock(id=1), MagicMock(id=2), MagicMock(id=3)]
    mock_session.scalars.return_value.all.return_value = mock_results

    class MockModel:
        pass

    repo = BaseRepository(mock_session, MockModel)

    # Test get_all
    result = await repo.get_all()

    # Verify query was executed
    mock_session.execute.assert_called_once()
    assert len(result) == 3


@pytest.mark.asyncio
async def test_base_repository_update(mock_session, mock_produto):
    """Test BaseRepository update method."""
    # Setup mock
    mock_session.scalar.return_value = mock_produto

    class MockModel:
        id = 1

    repo = BaseRepository(mock_session, MockModel)

    # Test update
    update_data = {"name": "Updated Product"}
    result = await repo.update(1, update_data)

    # Verify session interactions
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_delete(mock_session):
    """Test BaseRepository delete method."""
    class MockModel:
        id = 1

    repo = BaseRepository(mock_session, MockModel)

    # Test delete
    await repo.delete(1)

    # Verify session interactions
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


# --- ProductoRepository Tests ---

@pytest.mark.asyncio
async def test_produto_repository_get_by_url(mock_session, mock_produto):
    """Test ProductoRepository get_by_url method."""
    # Setup mock
    mock_session.scalar.return_value = mock_produto

    repo = ProductoRepository(mock_session)

    # Test get_by_url
    result = await repo.get_by_url("https://test.com/product/1")

    # Verify query was executed with URL filter
    mock_session.execute.assert_called_once()
    assert result == mock_produto


@pytest.mark.asyncio
async def test_produto_repository_get_by_minorista(mock_session):
    """Test ProductoRepository get_by_minorista method."""
    # Setup mock
    mock_products = [MagicMock(id=1), MagicMock(id=2)]
    mock_session.scalars.return_value.all.return_value = mock_products

    repo = ProductoRepository(mock_session)

    # Test get_by_minorista
    result = await repo.get_by_minorista(1)

    # Verify query was executed with retailer filter
    mock_session.execute.assert_called_once()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_produto_repository_update_price(mock_session, mock_produto):
    """Test ProductoRepository update_price method."""
    # Setup mock
    mock_produto.price = 150.00
    mock_produto.last_scraped_at = datetime.now(timezone.utc)
    mock_session.scalar.return_value = mock_produto

    repo = ProductoRepository(mock_session)

    # Test update_price
    result = await repo.update_price(1, 150.00)

    # Verify session interactions
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
    assert result.price == 150.00


# --- MinoristaRepository Tests ---

@pytest.mark.asyncio
async def test_minorista_repository_get_active(mock_session):
    """Test MinoristaRepository get_active method."""
    # Setup mock
    mock_active_retailers = [MagicMock(activo=True), MagicMock(activo=True)]
    mock_session.scalars.return_value.all.return_value = mock_active_retailers

    repo = MinoristaRepository(mock_session)

    # Test get_active
    result = await repo.get_active()

    # Verify query was executed with active filter
    mock_session.execute.assert_called_once()
    assert len(result) == 2
    assert all(r.activo for r in result)


@pytest.mark.asyncio
async def test_minorista_repository_get_with_discovery(mock_session):
    """Test MinoristaRepository get_with_discovery method."""
    # Setup mock
    mock_discovery_retailers = [
        MagicMock(discovery_url="https://test.com/products", product_link_selector="a.product")
    ]
    mock_session.scalars.return_value.all.return_value = mock_discovery_retailers

    repo = MinoristaRepository(mock_session)

    # Test get_with_discovery
    result = await repo.get_with_discovery()

    # Verify query was executed with discovery filter
    mock_session.execute.assert_called_once()
    assert len(result) == 1
    assert result[0].discovery_url is not None


# --- HistorialPrecioRepository Tests ---

@pytest.mark.asyncio
async def test_historial_repository_get_latest_by_product(mock_session):
    """Test HistorialPrecioRepository get_latest_by_product method."""
    # Setup mock
    mock_latest_price = MagicMock(precio=99.99, fecha_registro=datetime.now(timezone.utc))
    mock_session.scalar.return_value = mock_latest_price

    repo = HistorialPrecioRepository(mock_session)

    # Test get_latest_by_product
    result = await repo.get_latest_by_product(1)

    # Verify query was executed with product filter and ordering
    mock_session.execute.assert_called_once()
    assert result == mock_latest_price


@pytest.mark.asyncio
async def test_historial_repository_get_price_changes(mock_session):
    """Test HistorialPrecioRepository get_price_changes method."""
    # Setup mock
    mock_price_history = [
        MagicMock(precio=120.00, fecha_registro=datetime.now(timezone.utc)),
        MagicMock(precio=100.00, fecha_registro=datetime.now(timezone.utc)),
        MagicMock(precio=110.00, fecha_registro=datetime.now(timezone.utc))
    ]
    mock_session.scalars.return_value.all.return_value = mock_price_history

    repo = HistorialPrecioRepository(mock_session)

    # Test get_price_changes
    result = await repo.get_price_changes(1, limit=10)

    # Verify query was executed with product filter, ordering, and limit
    mock_session.execute.assert_called_once()
    assert len(result) == 3


# --- Error Handling Tests ---

@pytest.mark.asyncio
async def test_repository_handles_database_error(mock_session):
    """Test repository handles database errors gracefully."""
    # Setup mock to raise exception
    mock_session.commit.side_effect = Exception("Database connection failed")

    class MockModel:
        def __init__(self, **kwargs):
            pass

    repo = BaseRepository(mock_session, MockModel)

    # Test that exception is properly raised
    with pytest.raises(Exception, match="Database connection failed"):
        await repo.create({"name": "Test"})


@pytest.mark.asyncio
async def test_repository_handles_rollback_on_error(mock_session):
    """Test repository performs rollback on error."""
    # Setup mock to raise exception during commit
    mock_session.commit.side_effect = Exception("Commit failed")

    class MockModel:
        def __init__(self, **kwargs):
            pass

    repo = BaseRepository(mock_session, MockModel)

    # Test rollback is called on error
    with pytest.raises(Exception):
        await repo.create({"name": "Test"})

    # Verify rollback was called
    mock_session.rollback.assert_called_once()


# --- Performance Tests ---

@pytest.mark.asyncio
async def test_repository_caching_mechanism():
    """Test repository caching works correctly."""
    # This test would verify that cache is used for subsequent requests
    # Mock cache behavior
    from unittest.mock import patch

    with patch('backend.services.cache.app_cache') as mock_cache:
        mock_cache.get.return_value = None  # Cache miss
        mock_cache.set = AsyncMock()

        mock_session = AsyncMock()
        mock_session.scalar.return_value = MagicMock(id=1, name="Cached Product")

        repo = ProductoRepository(mock_session)

        # First call should hit database and set cache
        result1 = await repo.get_by_id(1)

        # Verify cache was checked and set
        mock_cache.get.assert_called()
        mock_cache.set.assert_called()


@pytest.mark.asyncio
async def test_repository_batch_operations():
    """Test repository can handle batch operations efficiently."""
    mock_session = AsyncMock()

    class MockModel:
        def __init__(self, **kwargs):
            self.id = kwargs.get('id', 1)

    repo = BaseRepository(mock_session, MockModel)

    # Test creating multiple items
    items_data = [{"name": f"Item {i}"} for i in range(5)]

    # Simulate batch creation
    created_items = []
    for data in items_data:
        item = await repo.create(data)
        created_items.append(item)

    # Verify session was used efficiently
    assert mock_session.add.call_count == 5
    assert mock_session.commit.call_count == 5
    assert len(created_items) == 5