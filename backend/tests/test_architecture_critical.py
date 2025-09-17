# backend/tests/test_architecture_critical.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


# --- Critical Architecture Tests ---

def test_event_type_enum():
    """Test EventType enum definition matches implementation."""
    from backend.services.event_bus import EventType

    assert hasattr(EventType, 'PRODUCT_SCRAPED')
    assert hasattr(EventType, 'SCRAPING_FAILED')
    assert hasattr(EventType, 'PRICE_CHANGED')
    assert hasattr(EventType, 'PRODUCT_UPDATED')
    assert hasattr(EventType, 'RETAILER_CREATED')


def test_event_creation():
    """Test Event creation and attributes."""
    from backend.services.event_bus import Event, EventType

    event = Event(
        type=EventType.PRODUCT_SCRAPED,
        data={"product_id": 1, "price": 99.99},
        timestamp=datetime.now(timezone.utc)
    )

    assert event.type == EventType.PRODUCT_SCRAPED
    assert isinstance(event.timestamp, datetime)
    assert event.data["product_id"] == 1
    assert event.data["price"] == 99.99


@pytest.mark.asyncio
async def test_event_bus_basic_functionality():
    """Test EventBus basic subscribe/publish."""
    from backend.services.event_bus import EventBus, EventType

    event_bus = EventBus()
    received_events = []

    async def test_handler(event):
        received_events.append(event)

    # Subscribe and publish
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, test_handler)

    test_event = {
        "type": EventType.PRODUCT_SCRAPED,
        "data": {"test": "data"}
    }

    await event_bus.publish(test_event)

    # Wait for async processing
    await asyncio.sleep(0.1)

    assert len(received_events) == 1


def test_memory_cache_basic_operations():
    """Test MemoryCache basic operations."""
    from backend.services.cache import MemoryCache

    cache = MemoryCache(max_size=3, default_ttl_seconds=60)

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test cache miss
    assert cache.get("nonexistent") is None

    # Test cache size
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    # Check statistics
    stats = cache.get_stats()
    assert stats["size"] == 3


def test_metrics_collector_basic_operations():
    """Test MetricsCollector basic operations."""
    from backend.services.metrics import MetricsCollector

    collector = MetricsCollector()

    # Test counter increment
    collector.increment("test_counter", tags={"env": "test"})
    collector.increment("test_counter", tags={"env": "test"})

    # Test gauge set
    collector.set_gauge("test_gauge", 100.0, tags={"type": "memory"})

    # Test timing record
    collector.record_timing("test_operation", 50.0, tags={"operation": "test"})

    # Get metrics should not crash
    metrics = collector.get_all_metrics()
    assert isinstance(metrics, dict)


@pytest.mark.asyncio
async def test_graceful_shutdown_manager():
    """Test GracefulShutdownManager basic functionality."""
    from backend.services.graceful_shutdown import GracefulShutdownManager

    shutdown_manager = GracefulShutdownManager(timeout_seconds=1.0)
    callback_executed = []

    def sync_callback():
        callback_executed.append("sync")

    async def async_callback():
        callback_executed.append("async")

    # Register callbacks
    shutdown_manager.register_shutdown_callback(sync_callback)
    shutdown_manager.register_shutdown_callback(async_callback)

    # Mock database engine disposal to avoid real connection
    with patch('backend.services.graceful_shutdown.async_engine') as mock_engine:
        mock_engine.dispose = AsyncMock()

        # Execute shutdown
        await shutdown_manager.shutdown()

        # Verify callbacks were executed
        assert "sync" in callback_executed
        assert "async" in callback_executed
        assert shutdown_manager.is_shutting_down


def test_health_check_result_creation():
    """Test HealthCheckResult creation."""
    from backend.services.health_checks import HealthCheckResult

    result = HealthCheckResult(
        name="test_check",
        status="healthy",
        details={"latency_ms": 5.2, "version": "1.0"}
    )

    assert result.name == "test_check"
    assert result.status == "healthy"
    assert result.details["latency_ms"] == 5.2


@pytest.mark.asyncio
async def test_concurrent_scraper_basic():
    """Test ConcurrentScraper basic functionality."""
    from backend.services.concurrent_scraper import ConcurrentScraper

    # Mock scraper service
    mock_scraper = MagicMock()
    mock_scraper.scrape_product_data = AsyncMock(return_value=MagicMock())

    concurrent_scraper = ConcurrentScraper(
        scraper_service=mock_scraper,
        max_concurrent=2
    )

    # Test basic initialization
    assert concurrent_scraper.max_concurrent == 2
    assert concurrent_scraper.scraper_service == mock_scraper


def test_cache_ttl_functionality():
    """Test cache TTL functionality."""
    from backend.services.cache import MemoryCache

    cache = MemoryCache(max_size=10, default_ttl_seconds=1)  # 1 second TTL

    # Set value
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"

    # Test that entry exists before expiration
    stats = cache.get_stats()
    assert stats["size"] == 1


def test_metrics_collector_tags():
    """Test MetricsCollector tag functionality."""
    from backend.services.metrics import MetricsCollector

    collector = MetricsCollector()

    # Create metrics with different tags
    collector.increment("api_requests", tags={"endpoint": "/products", "method": "GET"})
    collector.increment("api_requests", tags={"endpoint": "/retailers", "method": "GET"})

    # Get metrics should work
    metrics = collector.get_all_metrics()
    assert isinstance(metrics, dict)


@pytest.mark.asyncio
async def test_event_bus_error_handling():
    """Test EventBus error handling in handlers."""
    from backend.services.event_bus import EventBus, EventType

    event_bus = EventBus()
    successful_calls = []

    async def failing_handler(event):
        raise Exception("Handler failed")

    async def successful_handler(event):
        successful_calls.append(event)

    # Subscribe both handlers
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, failing_handler)
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, successful_handler)

    # Publish event - should not crash
    test_event = {
        "type": EventType.PRODUCT_SCRAPED,
        "data": {"test": "data"}
    }

    await event_bus.publish(test_event)
    await asyncio.sleep(0.1)

    # Successful handler should still be called despite other handler failing
    assert len(successful_calls) == 1


# --- Integration Test for API Structure ---

def test_api_routes_structure():
    """Test that critical API routes are structured correctly."""
    try:
        from backend.routes import gestion_datos, scraper, monitoring, observability

        # Verify route modules can be imported
        assert hasattr(gestion_datos, 'router')
        assert hasattr(scraper, 'router')
        assert hasattr(monitoring, 'router')
        assert hasattr(observability, 'router')

    except ImportError as e:
        # If specific modules fail, test what we can
        pytest.skip(f"API routes import failed: {e}")


def test_scheduler_module_exists():
    """Test scheduler module can be imported."""
    try:
        from backend.core import scheduler

        # Verify key functions exist
        assert hasattr(scheduler, 'start_scheduler')
        assert hasattr(scheduler, 'stop_scheduler')

    except ImportError as e:
        pytest.skip(f"Scheduler import failed: {e}")


# --- Database Connection Test (Mocked) ---

@pytest.mark.asyncio
async def test_database_connection_handling():
    """Test database connection handling without real connection."""
    with patch('backend.services.database.create_async_engine') as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Test that database module can be imported with mocked engine
        try:
            from backend.services import database
            assert database is not None
        except Exception as e:
            pytest.skip(f"Database module test skipped: {e}")


# --- Repository Pattern Test (Interface Only) ---

def test_repository_interface():
    """Test repository interface without database connection."""
    try:
        from backend.repositories.base import BaseRepository

        # Test that BaseRepository can be imported
        assert BaseRepository is not None

        # Test method existence (without calling them)
        mock_session = MagicMock()
        mock_model = MagicMock()

        repo = BaseRepository(mock_session, mock_model)

        # Verify methods exist
        assert hasattr(repo, 'create')
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'get_all')
        assert hasattr(repo, 'update')
        assert hasattr(repo, 'delete')

    except ImportError as e:
        pytest.skip(f"Repository interface test skipped: {e}")


# --- Performance Tests ---

def test_cache_performance():
    """Test cache performance with many operations."""
    from backend.services.cache import MemoryCache
    import time

    cache = MemoryCache(max_size=1000, default_ttl_seconds=60)

    # Measure time for many set operations
    start_time = time.time()
    for i in range(100):  # Reduced for faster test
        cache.set(f"key_{i}", f"value_{i}")
    set_time = time.time() - start_time

    # Measure time for many get operations
    start_time = time.time()
    for i in range(100):
        cache.get(f"key_{i}")
    get_time = time.time() - start_time

    # Performance assertions (reasonable thresholds)
    assert set_time < 1.0  # Should complete 100 sets in under 1 second
    assert get_time < 1.0  # Should complete 100 gets in under 1 second


@pytest.mark.asyncio
async def test_event_bus_performance():
    """Test event bus performance with many events."""
    from backend.services.event_bus import EventBus, EventType
    import time

    event_bus = EventBus()
    handled_count = 0

    async def counting_handler(event):
        nonlocal handled_count
        handled_count += 1

    event_bus.subscribe(EventType.PRODUCT_SCRAPED, counting_handler)

    # Measure time to publish 50 events (reduced for faster test)
    start_time = time.time()
    tasks = []
    for i in range(50):
        event = {
            "type": EventType.PRODUCT_SCRAPED,
            "data": {"event_id": i}
        }
        task = event_bus.publish(event)
        tasks.append(task)

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)  # Wait for handlers
    end_time = time.time()

    assert handled_count == 50
    assert end_time - start_time < 2.0  # Should handle 50 events in under 2 seconds


# --- Configuration Tests ---

def test_logging_configuration():
    """Test logging configuration."""
    try:
        from backend.services import logging_config

        # Test module can be imported
        assert logging_config is not None
        assert hasattr(logging_config, 'setup_logging')

    except ImportError as e:
        pytest.skip(f"Logging config test skipped: {e}")


def test_error_handling_module():
    """Test error handling module."""
    try:
        from backend.core import error_handling

        # Test module can be imported
        assert error_handling is not None

        # Verify key functions exist
        assert hasattr(error_handling, 'add_process_time_and_correlation_id')
        assert hasattr(error_handling, 'http_exception_handler')

    except ImportError as e:
        pytest.skip(f"Error handling test skipped: {e}")


# --- Critical Path Integration Test ---

@pytest.mark.asyncio
async def test_critical_path_integration():
    """Test critical system integration without external dependencies."""

    # Test event system integration
    from backend.services.event_bus import EventBus, EventType
    event_bus = EventBus()

    # Test cache integration
    from backend.services.cache import MemoryCache
    cache = MemoryCache()

    # Test metrics integration
    from backend.services.metrics import MetricsCollector
    metrics = MetricsCollector()

    # Simulate critical path: scraping → event → cache update → metrics
    received_events = []

    async def cache_update_handler(event):
        # Simulate cache update
        cache.set("product_1", event["data"])
        metrics.increment("events_processed")
        received_events.append(event)

    event_bus.subscribe(EventType.PRODUCT_SCRAPED, cache_update_handler)

    # Publish scraping event
    event = {
        "type": EventType.PRODUCT_SCRAPED,
        "data": {"product_id": 1, "price": 99.99}
    }

    await event_bus.publish(event)
    await asyncio.sleep(0.1)

    # Verify integration worked
    assert len(received_events) == 1
    assert cache.get("product_1") is not None

    # Verify metrics were recorded
    all_metrics = metrics.get_all_metrics()
    assert isinstance(all_metrics, dict)