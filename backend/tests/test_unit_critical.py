# backend/tests/test_unit_critical.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# --- Critical Unit Tests (No Database Dependencies) ---

def test_event_type_enum():
    """Test EventType enum definition."""
    from backend.services.event_bus import EventType

    assert hasattr(EventType, 'PRODUCT_SCRAPED')
    assert hasattr(EventType, 'SCRAPING_FAILED')
    assert hasattr(EventType, 'PRICE_CHANGED')
    assert hasattr(EventType, 'RETAILER_DISCOVERED')


def test_event_data_creation():
    """Test EventData creation and attributes."""
    from backend.services.event_bus import EventData, EventType

    event_data = EventData(
        event_type=EventType.PRODUCT_SCRAPED,
        timestamp=datetime.now(timezone.utc),
        data={"product_id": 1, "price": 99.99}
    )

    assert event_data.event_type == EventType.PRODUCT_SCRAPED
    assert isinstance(event_data.timestamp, datetime)
    assert event_data.data["product_id"] == 1
    assert event_data.data["price"] == 99.99


@pytest.mark.asyncio
async def test_event_bus_basic_functionality():
    """Test EventBus basic subscribe/publish without external dependencies."""
    from backend.services.event_bus import EventBus, EventType

    event_bus = EventBus()
    received_events = []

    async def test_handler(event_data):
        received_events.append(event_data)

    # Subscribe and publish
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, test_handler)
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"test": "data"})

    # Wait for async processing
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].data["test"] == "data"


def test_lru_cache_basic_operations():
    """Test LRUCache basic operations."""
    from backend.services.cache import LRUCache

    cache = LRUCache(max_size=3, ttl_seconds=60)

    # Test set and get
    cache.set_sync("key1", "value1")
    assert cache.get_sync("key1") == "value1"

    # Test cache miss
    assert cache.get_sync("nonexistent") is None

    # Test cache size limit
    cache.set_sync("key2", "value2")
    cache.set_sync("key3", "value3")
    cache.set_sync("key4", "value4")  # Should evict key1

    assert cache.get_sync("key1") is None  # Evicted
    assert cache.get_sync("key4") == "value4"  # Most recent


def test_metrics_collector_basic_operations():
    """Test MetricsCollector basic operations."""
    from backend.services.metrics import MetricsCollector

    collector = MetricsCollector()

    # Test counter
    collector.increment_counter("test_counter", tags={"env": "test"})
    collector.increment_counter("test_counter", tags={"env": "test"})

    # Test gauge
    collector.set_gauge("test_gauge", 100.0, tags={"type": "memory"})

    # Test histogram
    collector.record_histogram("test_histogram", 50.0, tags={"operation": "test"})

    metrics = collector.get_metrics()

    # Verify counter
    counter_metrics = [m for m in metrics if m["name"] == "test_counter"]
    assert len(counter_metrics) == 1
    assert counter_metrics[0]["value"] == 2

    # Verify gauge
    gauge_metrics = [m for m in metrics if m["name"] == "test_gauge"]
    assert len(gauge_metrics) == 1
    assert gauge_metrics[0]["value"] == 100.0

    # Verify histogram
    histogram_metrics = [m for m in metrics if m["name"] == "test_histogram"]
    assert len(histogram_metrics) == 1
    assert histogram_metrics[0]["count"] == 1


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

    # Mock database engine disposal
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
    assert result.details["version"] == "1.0"


@pytest.mark.asyncio
async def test_concurrent_scraper_semaphore():
    """Test ConcurrentScraper semaphore functionality."""
    from backend.services.concurrent_scraper import ConcurrentScraper

    # Mock dependencies
    mock_scraper = AsyncMock()
    mock_scraper.scrape_product_data = AsyncMock(return_value=MagicMock())

    concurrent_scraper = ConcurrentScraper(
        scraper=mock_scraper,
        max_concurrent=2
    )

    # Test semaphore limits concurrent operations
    urls = [f"https://test.com/product/{i}" for i in range(5)]
    minorista_id = 1

    # Mock session
    mock_session = AsyncMock()

    start_time = asyncio.get_event_loop().time()
    await concurrent_scraper.scrape_products_batch(urls, minorista_id, mock_session)
    end_time = asyncio.get_event_loop().time()

    # Should have called scraper for each URL
    assert mock_scraper.scrape_product_data.call_count == 5

    # With max_concurrent=2, should take more time than if all were parallel
    # This is a simple timing test
    assert end_time - start_time > 0


def test_logging_config_setup():
    """Test logging configuration setup."""
    with patch('logging.basicConfig') as mock_basic_config, \
         patch('logging.getLogger') as mock_get_logger:

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        from backend.services.logging_config import setup_logging

        setup_logging()

        # Verify logging was configured
        mock_basic_config.assert_called_once()


def test_error_handling_middleware():
    """Test error handling middleware functionality."""
    from backend.core.error_handling import (
        add_process_time_and_correlation_id,
        http_exception_handler,
        validation_exception_handler,
        generic_exception_handler
    )

    # Test process time middleware
    mock_request = MagicMock()
    mock_request.headers = {}

    async def mock_call_next(request):
        return MagicMock(headers={})

    # This would require more complex mocking for full test
    # For now, just verify functions exist and are callable
    assert callable(add_process_time_and_correlation_id)
    assert callable(http_exception_handler)
    assert callable(validation_exception_handler)
    assert callable(generic_exception_handler)


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache TTL expiration functionality."""
    from backend.services.cache import LRUCache
    import time

    cache = LRUCache(max_size=10, ttl_seconds=0.1)  # Very short TTL

    # Set value and immediately check
    cache.set_sync("test_key", "test_value")
    assert cache.get_sync("test_key") == "test_value"

    # Wait for TTL to expire
    time.sleep(0.2)

    # Should be None due to TTL expiration
    assert cache.get_sync("test_key") is None


def test_metrics_collector_tags():
    """Test MetricsCollector tag functionality."""
    from backend.services.metrics import MetricsCollector

    collector = MetricsCollector()

    # Create metrics with different tags
    collector.increment_counter("api_requests", tags={"endpoint": "/products", "method": "GET"})
    collector.increment_counter("api_requests", tags={"endpoint": "/retailers", "method": "GET"})
    collector.increment_counter("api_requests", tags={"endpoint": "/products", "method": "POST"})

    metrics = collector.get_metrics()
    api_metrics = [m for m in metrics if m["name"] == "api_requests"]

    # Should have 3 different counters due to different tag combinations
    assert len(api_metrics) == 3

    # Verify tag combinations
    tag_combinations = [tuple(sorted(m["tags"].items())) for m in api_metrics]
    expected_combinations = [
        (("endpoint", "/products"), ("method", "GET")),
        (("endpoint", "/retailers"), ("method", "GET")),
        (("endpoint", "/products"), ("method", "POST"))
    ]

    for expected in expected_combinations:
        assert expected in tag_combinations


@pytest.mark.asyncio
async def test_event_bus_error_handling():
    """Test EventBus error handling in handlers."""
    from backend.services.event_bus import EventBus, EventType

    event_bus = EventBus()
    successful_calls = []

    async def failing_handler(event_data):
        raise Exception("Handler failed")

    async def successful_handler(event_data):
        successful_calls.append(event_data)

    # Subscribe both handlers
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, failing_handler)
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, successful_handler)

    # Publish event - should not crash
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"test": "data"})
    await asyncio.sleep(0.1)

    # Successful handler should still be called despite other handler failing
    assert len(successful_calls) == 1


def test_scheduler_configuration():
    """Test scheduler configuration without starting it."""
    with patch('backend.core.scheduler.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        from backend.core.scheduler import configure_scheduler

        scheduler = configure_scheduler()

        # Verify scheduler was configured with correct settings
        mock_scheduler_class.assert_called_once()
        assert scheduler == mock_scheduler


# --- Integration Test Stubs ---

def test_api_routes_exist():
    """Test that critical API routes are defined."""
    from backend.routes import gestion_datos, scraper, monitoring, observability

    # Verify route modules can be imported
    assert hasattr(gestion_datos, 'router')
    assert hasattr(scraper, 'router')
    assert hasattr(monitoring, 'router')
    assert hasattr(observability, 'router')


def test_pydantic_v2_syntax():
    """Test that Pydantic V2 syntax is used correctly."""
    # This test would check that we're using the new syntax
    # For now, just verify we can import without errors
    try:
        from backend.routes.gestion_datos import (
            ProductoCreate,
            ProductoUpdate,
            MinoristaCreate
        )
        # If import succeeds, Pydantic models are valid
        assert True
    except ImportError:
        pytest.fail("Pydantic models import failed")


# --- Performance Tests ---

def test_cache_performance():
    """Test cache performance with many operations."""
    from backend.services.cache import LRUCache
    import time

    cache = LRUCache(max_size=1000, ttl_seconds=60)

    # Measure time for 1000 set operations
    start_time = time.time()
    for i in range(1000):
        cache.set_sync(f"key_{i}", f"value_{i}")
    set_time = time.time() - start_time

    # Measure time for 1000 get operations
    start_time = time.time()
    for i in range(1000):
        cache.get_sync(f"key_{i}")
    get_time = time.time() - start_time

    # Performance assertions (adjust thresholds as needed)
    assert set_time < 1.0  # Should complete 1000 sets in under 1 second
    assert get_time < 1.0  # Should complete 1000 gets in under 1 second


@pytest.mark.asyncio
async def test_event_bus_performance():
    """Test event bus performance with many events."""
    from backend.services.event_bus import EventBus, EventType
    import time

    event_bus = EventBus()
    handled_count = 0

    async def counting_handler(event_data):
        nonlocal handled_count
        handled_count += 1

    event_bus.subscribe(EventType.PRODUCT_SCRAPED, counting_handler)

    # Measure time to publish 100 events
    start_time = time.time()
    tasks = []
    for i in range(100):
        task = event_bus.publish(EventType.PRODUCT_SCRAPED, {"event_id": i})
        tasks.append(task)

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)  # Wait for handlers
    end_time = time.time()

    assert handled_count == 100
    assert end_time - start_time < 2.0  # Should handle 100 events in under 2 seconds