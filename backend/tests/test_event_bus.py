# backend/tests/test_event_bus.py

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from backend.services.event_bus import EventBus, EventType, EventData
from backend.services.event_handlers import (
    handle_product_scraped,
    handle_scraping_failed,
    handle_price_changed
)


@pytest.fixture
def event_bus():
    """Create fresh EventBus instance for each test."""
    return EventBus()


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return EventData(
        event_type=EventType.PRODUCT_SCRAPED,
        timestamp=datetime.now(timezone.utc),
        data={
            "product_id": 1,
            "product_name": "Test Product",
            "price": 99.99,
            "minorista_id": 1,
            "product_url": "https://test.com/product/1"
        }
    )


# --- EventBus Core Tests ---

@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish(event_bus):
    """Test basic subscribe and publish functionality."""
    received_events = []

    async def test_handler(event_data: EventData):
        received_events.append(event_data)

    # Subscribe handler
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, test_handler)

    # Publish event
    test_data = {
        "product_id": 1,
        "product_name": "Test Product",
        "price": 99.99
    }

    await event_bus.publish(EventType.PRODUCT_SCRAPED, test_data)

    # Wait for async event processing
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.PRODUCT_SCRAPED
    assert received_events[0].data["product_id"] == 1
    assert received_events[0].data["product_name"] == "Test Product"


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers(event_bus):
    """Test multiple subscribers for same event type."""
    handler1_calls = []
    handler2_calls = []

    async def handler1(event_data: EventData):
        handler1_calls.append(event_data)

    async def handler2(event_data: EventData):
        handler2_calls.append(event_data)

    # Subscribe both handlers
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, handler1)
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, handler2)

    # Publish event
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"test": "data"})
    await asyncio.sleep(0.1)

    assert len(handler1_calls) == 1
    assert len(handler2_calls) == 1
    assert handler1_calls[0].data["test"] == "data"
    assert handler2_calls[0].data["test"] == "data"


@pytest.mark.asyncio
async def test_event_bus_unsubscribe(event_bus):
    """Test unsubscribe functionality."""
    received_events = []

    async def test_handler(event_data: EventData):
        received_events.append(event_data)

    # Subscribe and publish
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, test_handler)
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"first": "event"})
    await asyncio.sleep(0.1)

    # Unsubscribe and publish again
    event_bus.unsubscribe(EventType.PRODUCT_SCRAPED, test_handler)
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"second": "event"})
    await asyncio.sleep(0.1)

    # Should only receive first event
    assert len(received_events) == 1
    assert received_events[0].data["first"] == "event"


@pytest.mark.asyncio
async def test_event_bus_error_handling(event_bus):
    """Test event bus handles errors in handlers gracefully."""
    successful_calls = []

    async def failing_handler(event_data: EventData):
        raise Exception("Handler error")

    async def successful_handler(event_data: EventData):
        successful_calls.append(event_data)

    # Subscribe both handlers
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, failing_handler)
    event_bus.subscribe(EventType.PRODUCT_SCRAPED, successful_handler)

    # Publish event - should not crash even with failing handler
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {"test": "data"})
    await asyncio.sleep(0.1)

    # Successful handler should still be called
    assert len(successful_calls) == 1


@pytest.mark.asyncio
async def test_event_bus_concurrent_publishing(event_bus):
    """Test event bus handles concurrent event publishing."""
    received_events = []

    async def test_handler(event_data: EventData):
        await asyncio.sleep(0.01)  # Simulate async work
        received_events.append(event_data)

    event_bus.subscribe(EventType.PRODUCT_SCRAPED, test_handler)

    # Publish multiple events concurrently
    tasks = []
    for i in range(10):
        task = event_bus.publish(EventType.PRODUCT_SCRAPED, {"event_id": i})
        tasks.append(task)

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.2)  # Wait for all handlers to complete

    assert len(received_events) == 10
    event_ids = [event.data["event_id"] for event in received_events]
    assert sorted(event_ids) == list(range(10))


# --- Event Handler Tests ---

@pytest.mark.asyncio
async def test_handle_product_scraped():
    """Test product scraped event handler."""
    # Mock dependencies
    mock_cache = AsyncMock()
    mock_metrics = MagicMock()

    event_data = EventData(
        event_type=EventType.PRODUCT_SCRAPED,
        timestamp=datetime.now(timezone.utc),
        data={
            "product_id": 1,
            "product_name": "Test Product",
            "price": 99.99,
            "minorista_id": 1,
            "product_url": "https://test.com/product/1"
        }
    )

    # Patch dependencies and call handler
    with pytest.MonkeyPatch.context() as m:
        m.setattr("backend.services.event_handlers.app_cache", mock_cache)
        m.setattr("backend.services.event_handlers.metrics_collector", mock_metrics)

        await handle_product_scraped(event_data)

        # Verify cache invalidation was called
        mock_cache.delete.assert_called()

        # Verify metrics were recorded
        mock_metrics.increment_counter.assert_called()


@pytest.mark.asyncio
async def test_handle_scraping_failed():
    """Test scraping failed event handler."""
    mock_logger = MagicMock()
    mock_metrics = MagicMock()

    event_data = EventData(
        event_type=EventType.SCRAPING_FAILED,
        timestamp=datetime.now(timezone.utc),
        data={
            "product_url": "https://test.com/product/1",
            "minorista_id": 1,
            "error": "Network timeout",
            "retry_count": 3
        }
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr("backend.services.event_handlers.logger", mock_logger)
        m.setattr("backend.services.event_handlers.metrics_collector", mock_metrics)

        await handle_scraping_failed(event_data)

        # Verify error was logged
        mock_logger.error.assert_called()

        # Verify failure metrics were recorded
        mock_metrics.increment_counter.assert_called_with(
            "scraping_failures_total",
            tags={"minorista_id": 1, "error_type": "Network timeout"}
        )


@pytest.mark.asyncio
async def test_handle_price_changed():
    """Test price changed event handler."""
    mock_logger = MagicMock()
    mock_metrics = MagicMock()

    event_data = EventData(
        event_type=EventType.PRICE_CHANGED,
        timestamp=datetime.now(timezone.utc),
        data={
            "product_id": 1,
            "product_name": "Test Product",
            "old_price": 99.99,
            "new_price": 89.99,
            "price_change_percent": -10.0,
            "minorista_id": 1
        }
    )

    with pytest.MonkeyPatch.context() as m:
        m.setattr("backend.services.event_handlers.logger", mock_logger)
        m.setattr("backend.services.event_handlers.metrics_collector", mock_metrics)

        await handle_price_changed(event_data)

        # Verify price change was logged
        mock_logger.info.assert_called()

        # Verify price change metrics were recorded
        mock_metrics.record_histogram.assert_called()


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_event_system_integration(event_bus):
    """Test complete event system integration."""
    # Track all event handling
    handled_events = {
        EventType.PRODUCT_SCRAPED: [],
        EventType.SCRAPING_FAILED: [],
        EventType.PRICE_CHANGED: []
    }

    async def track_handler(event_type):
        async def handler(event_data: EventData):
            handled_events[event_type].append(event_data)
        return handler

    # Subscribe tracking handlers for all event types
    for event_type in EventType:
        handler = await track_handler(event_type)
        event_bus.subscribe(event_type, handler)

    # Publish various events
    await event_bus.publish(EventType.PRODUCT_SCRAPED, {
        "product_id": 1,
        "price": 99.99
    })

    await event_bus.publish(EventType.SCRAPING_FAILED, {
        "product_url": "https://test.com/failed",
        "error": "Timeout"
    })

    await event_bus.publish(EventType.PRICE_CHANGED, {
        "product_id": 1,
        "old_price": 99.99,
        "new_price": 89.99
    })

    await asyncio.sleep(0.1)

    # Verify all events were handled
    assert len(handled_events[EventType.PRODUCT_SCRAPED]) == 1
    assert len(handled_events[EventType.SCRAPING_FAILED]) == 1
    assert len(handled_events[EventType.PRICE_CHANGED]) == 1


@pytest.mark.asyncio
async def test_event_bus_performance(event_bus):
    """Test event bus performance with high load."""
    import time

    handled_count = 0

    async def counting_handler(event_data: EventData):
        nonlocal handled_count
        handled_count += 1

    event_bus.subscribe(EventType.PRODUCT_SCRAPED, counting_handler)

    # Measure time to publish and handle 1000 events
    start_time = time.time()

    tasks = []
    for i in range(1000):
        task = event_bus.publish(EventType.PRODUCT_SCRAPED, {"event_id": i})
        tasks.append(task)

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.5)  # Wait for all handlers

    end_time = time.time()
    duration = end_time - start_time

    assert handled_count == 1000
    assert duration < 2.0  # Should handle 1000 events in under 2 seconds


@pytest.mark.asyncio
async def test_event_data_validation():
    """Test EventData validation and serialization."""
    # Test valid event data
    valid_data = EventData(
        event_type=EventType.PRODUCT_SCRAPED,
        timestamp=datetime.now(timezone.utc),
        data={"product_id": 1, "price": 99.99}
    )

    assert valid_data.event_type == EventType.PRODUCT_SCRAPED
    assert isinstance(valid_data.timestamp, datetime)
    assert valid_data.data["product_id"] == 1

    # Test event data with complex nested data
    complex_data = EventData(
        event_type=EventType.SCRAPING_FAILED,
        timestamp=datetime.now(timezone.utc),
        data={
            "error_details": {
                "error_type": "NetworkError",
                "status_code": 500,
                "retry_attempts": [
                    {"attempt": 1, "delay": 1.0},
                    {"attempt": 2, "delay": 2.0}
                ]
            }
        }
    )

    assert complex_data.data["error_details"]["error_type"] == "NetworkError"
    assert len(complex_data.data["error_details"]["retry_attempts"]) == 2