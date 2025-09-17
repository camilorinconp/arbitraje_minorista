# backend/tests/test_observability.py

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.health_checks import (
    DatabaseHealthCheck,
    CacheHealthCheck,
    ScraperHealthCheck,
    SchedulerHealthCheck,
    SystemResourcesHealthCheck
)
from backend.services.metrics import MetricsCollector
from backend.services.cache import LRUCache


client = TestClient(app)


# --- Health Check Tests ---

@pytest.mark.asyncio
async def test_database_health_check():
    """Test database health check functionality."""
    with patch('backend.services.health_checks.async_engine') as mock_engine:
        mock_connection = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.return_value.scalar.return_value = 1

        health_check = DatabaseHealthCheck()
        result = await health_check.check()

        assert result.status == "healthy"
        assert result.name == "database"
        assert "latency_ms" in result.details
        mock_connection.execute.assert_called_once()


@pytest.mark.asyncio
async def test_database_health_check_failure():
    """Test database health check when database is down."""
    with patch('backend.services.health_checks.async_engine') as mock_engine:
        mock_engine.connect.side_effect = Exception("Connection failed")

        health_check = DatabaseHealthCheck()
        result = await health_check.check()

        assert result.status == "unhealthy"
        assert result.name == "database"
        assert "Connection failed" in result.details["error"]


@pytest.mark.asyncio
async def test_cache_health_check():
    """Test cache health check functionality."""
    cache = LRUCache(max_size=100, ttl_seconds=60)

    # Add some test data to cache
    await cache.set("test_key", "test_value")

    with patch('backend.services.health_checks.app_cache', cache):
        health_check = CacheHealthCheck()
        result = await health_check.check()

        assert result.status == "healthy"
        assert result.name == "cache"
        assert result.details["cache_size"] >= 1
        assert "hit_rate" in result.details


@pytest.mark.asyncio
async def test_scraper_health_check():
    """Test scraper health check functionality."""
    with patch('backend.services.health_checks.async_playwright') as mock_playwright:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser

        health_check = ScraperHealthCheck()
        result = await health_check.check()

        assert result.status == "healthy"
        assert result.name == "scraper"
        assert "browser_launch_time_ms" in result.details


@pytest.mark.asyncio
async def test_scraper_health_check_failure():
    """Test scraper health check when browser fails to launch."""
    with patch('backend.services.health_checks.async_playwright') as mock_playwright:
        mock_playwright.return_value.__aenter__.side_effect = Exception("Browser launch failed")

        health_check = ScraperHealthCheck()
        result = await health_check.check()

        assert result.status == "unhealthy"
        assert result.name == "scraper"
        assert "Browser launch failed" in result.details["error"]


@pytest.mark.asyncio
async def test_scheduler_health_check():
    """Test scheduler health check functionality."""
    with patch('backend.services.health_checks.scheduler') as mock_scheduler:
        mock_scheduler.running = True
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock()]

        health_check = SchedulerHealthCheck()
        result = await health_check.check()

        assert result.status == "healthy"
        assert result.name == "scheduler"
        assert result.details["is_running"] is True
        assert result.details["active_jobs"] == 2


@pytest.mark.asyncio
async def test_system_resources_health_check():
    """Test system resources health check functionality."""
    with patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.cpu_percent') as mock_cpu:

        # Mock system stats
        mock_memory.return_value.percent = 45.0
        mock_disk.return_value.percent = 30.0
        mock_cpu.return_value = 25.0

        health_check = SystemResourcesHealthCheck()
        result = await health_check.check()

        assert result.status == "healthy"
        assert result.name == "system_resources"
        assert result.details["memory_usage_percent"] == 45.0
        assert result.details["disk_usage_percent"] == 30.0
        assert result.details["cpu_usage_percent"] == 25.0


@pytest.mark.asyncio
async def test_system_resources_health_check_high_usage():
    """Test system resources health check with high resource usage."""
    with patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.cpu_percent') as mock_cpu:

        # Mock high usage
        mock_memory.return_value.percent = 95.0  # High memory
        mock_disk.return_value.percent = 92.0    # High disk
        mock_cpu.return_value = 85.0             # High CPU

        health_check = SystemResourcesHealthCheck()
        result = await health_check.check()

        assert result.status == "unhealthy"
        assert result.name == "system_resources"
        assert result.details["memory_usage_percent"] == 95.0


# --- Metrics Tests ---

def test_metrics_collector_counter():
    """Test metrics collector counter functionality."""
    collector = MetricsCollector()

    # Increment counter multiple times
    collector.increment_counter("test_counter", tags={"env": "test"})
    collector.increment_counter("test_counter", tags={"env": "test"})
    collector.increment_counter("test_counter", tags={"env": "prod"})

    metrics = collector.get_metrics()

    # Should have two different counters due to different tags
    test_counters = [m for m in metrics if m["name"] == "test_counter"]
    assert len(test_counters) == 2

    # Check values
    test_env_counter = next(m for m in test_counters if m["tags"]["env"] == "test")
    prod_env_counter = next(m for m in test_counters if m["tags"]["env"] == "prod")

    assert test_env_counter["value"] == 2
    assert prod_env_counter["value"] == 1


def test_metrics_collector_gauge():
    """Test metrics collector gauge functionality."""
    collector = MetricsCollector()

    # Set gauge values
    collector.set_gauge("test_gauge", 100.0, tags={"type": "memory"})
    collector.set_gauge("test_gauge", 75.0, tags={"type": "cpu"})

    metrics = collector.get_metrics()

    gauge_metrics = [m for m in metrics if m["name"] == "test_gauge"]
    assert len(gauge_metrics) == 2

    memory_gauge = next(m for m in gauge_metrics if m["tags"]["type"] == "memory")
    cpu_gauge = next(m for m in gauge_metrics if m["tags"]["type"] == "cpu")

    assert memory_gauge["value"] == 100.0
    assert cpu_gauge["value"] == 75.0


def test_metrics_collector_histogram():
    """Test metrics collector histogram functionality."""
    collector = MetricsCollector()

    # Record histogram values
    values = [10.0, 20.0, 30.0, 15.0, 25.0]
    for value in values:
        collector.record_histogram("test_histogram", value, tags={"operation": "scraping"})

    metrics = collector.get_metrics()

    histogram_metrics = [m for m in metrics if m["name"] == "test_histogram"]
    assert len(histogram_metrics) == 1

    histogram = histogram_metrics[0]
    assert histogram["count"] == 5
    assert histogram["sum"] == sum(values)
    assert histogram["min"] == min(values)
    assert histogram["max"] == max(values)
    assert histogram["avg"] == sum(values) / len(values)


def test_metrics_collector_timing_context():
    """Test metrics collector timing context manager."""
    collector = MetricsCollector()

    with collector.time_operation("test_operation", tags={"type": "database"}):
        time.sleep(0.1)  # Simulate work

    metrics = collector.get_metrics()

    timing_metrics = [m for m in metrics if m["name"] == "test_operation"]
    assert len(timing_metrics) == 1

    timing = timing_metrics[0]
    assert timing["count"] == 1
    assert timing["avg"] >= 0.1  # Should be at least 100ms


def test_metrics_collector_cleanup():
    """Test metrics collector cleanup functionality."""
    collector = MetricsCollector()

    # Create metrics with different timestamps
    current_time = time.time()
    old_time = current_time - 7200  # 2 hours ago

    # Manually set old metrics
    collector.counters["old_counter"] = {
        "value": 10,
        "tags": {},
        "timestamp": old_time
    }

    collector.increment_counter("new_counter")

    # Clean up old metrics (older than 1 hour)
    collector.cleanup_old_metrics(max_age_seconds=3600)

    metrics = collector.get_metrics()
    metric_names = [m["name"] for m in metrics]

    assert "new_counter" in metric_names
    assert "old_counter" not in metric_names


# --- API Endpoint Tests ---

def test_health_endpoint():
    """Test /observability/health endpoint."""
    with patch('backend.routes.observability.health_checks') as mock_health_checks:
        # Mock health check results
        mock_results = [
            MagicMock(name="database", status="healthy", details={"latency_ms": 5.2}),
            MagicMock(name="cache", status="healthy", details={"cache_size": 10}),
            MagicMock(name="scraper", status="healthy", details={"browser_version": "1.0"}),
        ]
        mock_health_checks.__iter__.return_value = mock_results

        for result in mock_results:
            result.check = AsyncMock(return_value=result)

        response = client.get("/observability/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert len(data["checks"]) == 3
        assert all(check["status"] == "healthy" for check in data["checks"])


def test_health_endpoint_with_failure():
    """Test /observability/health endpoint when some checks fail."""
    with patch('backend.routes.observability.health_checks') as mock_health_checks:
        # Mock mixed health check results
        mock_results = [
            MagicMock(name="database", status="healthy", details={"latency_ms": 5.2}),
            MagicMock(name="cache", status="unhealthy", details={"error": "Connection failed"}),
        ]
        mock_health_checks.__iter__.return_value = mock_results

        for result in mock_results:
            result.check = AsyncMock(return_value=result)

        response = client.get("/observability/health")

        assert response.status_code == 503  # Service Unavailable
        data = response.json()

        assert data["status"] == "unhealthy"
        assert len(data["checks"]) == 2


def test_metrics_endpoint():
    """Test /observability/metrics endpoint."""
    with patch('backend.routes.observability.metrics_collector') as mock_collector:
        mock_metrics = [
            {
                "name": "api_requests_total",
                "type": "counter",
                "value": 100,
                "tags": {"endpoint": "/products"}
            },
            {
                "name": "scraping_duration",
                "type": "histogram",
                "count": 50,
                "sum": 250.5,
                "avg": 5.01
            }
        ]
        mock_collector.get_metrics.return_value = mock_metrics

        response = client.get("/observability/metrics")

        assert response.status_code == 200
        data = response.json()

        assert len(data["metrics"]) == 2
        assert data["metrics"][0]["name"] == "api_requests_total"
        assert data["metrics"][1]["name"] == "scraping_duration"


def test_ready_endpoint():
    """Test /observability/ready endpoint (Kubernetes readiness probe)."""
    response = client.get("/observability/ready")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"
    assert "timestamp" in data


def test_live_endpoint():
    """Test /observability/live endpoint (Kubernetes liveness probe)."""
    response = client.get("/observability/live")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "alive"
    assert "uptime_seconds" in data


def test_system_info_endpoint():
    """Test /observability/system endpoint."""
    with patch('platform.system') as mock_system, \
         patch('platform.python_version') as mock_python_version, \
         patch('psutil.virtual_memory') as mock_memory:

        mock_system.return_value = "Linux"
        mock_python_version.return_value = "3.11.0"
        mock_memory.return_value.total = 8589934592  # 8GB

        response = client.get("/observability/system")

        assert response.status_code == 200
        data = response.json()

        assert data["platform"] == "Linux"
        assert data["python_version"] == "3.11.0"
        assert "memory_total_bytes" in data