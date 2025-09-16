# backend/services/health_checks.py

import asyncio
import logging
import time
from typing import Dict, Any
from datetime import datetime, timedelta

from ..services.database import AsyncSessionLocal, async_engine
from ..services.cache import app_cache
from ..repositories import ProductoRepository, MinoristaRepository
from .metrics import health_checker, metrics_collector

logger = logging.getLogger(__name__)


async def database_health_check() -> Dict[str, Any]:
    """
    Check de salud de la base de datos.
    """
    try:
        start_time = time.time()

        async with AsyncSessionLocal() as db:
            # Test simple query
            result = await db.execute("SELECT 1")
            _ = result.scalar()

            # Check connection pool stats
            pool = async_engine.pool
            pool_stats = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }

        query_time = time.time() - start_time

        return {
            "healthy": True,
            "query_time_ms": round(query_time * 1000, 2),
            "pool_stats": pool_stats,
            "message": "Database connection successful"
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "message": "Database connection failed"
        }


async def cache_health_check() -> Dict[str, Any]:
    """
    Check de salud del sistema de cache.
    """
    try:
        start_time = time.time()

        # Test cache operations
        test_key = "health_check_test"
        test_value = {"timestamp": datetime.now().isoformat()}

        await app_cache.set(test_key, test_value, ttl_seconds=60)
        retrieved_value = await app_cache.get(test_key)
        await app_cache.delete(test_key)

        operation_time = time.time() - start_time

        # Get cache stats
        cache_stats = await app_cache.get_stats()

        return {
            "healthy": retrieved_value is not None,
            "operation_time_ms": round(operation_time * 1000, 2),
            "cache_stats": cache_stats,
            "message": "Cache operations successful" if retrieved_value else "Cache test failed"
        }

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "message": "Cache operations failed"
        }


async def scraping_system_health_check() -> Dict[str, Any]:
    """
    Check de salud del sistema de scraping.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Check active retailers
            minorista_repo = MinoristaRepository(db)
            active_retailers = await minorista_repo.get_active_retailers()

            # Check recent scraping activity
            producto_repo = ProductoRepository(db)
            recent_products = await producto_repo.get_recently_scraped_products(hours=1)

            # Get scraping metrics from last hour
            scraping_metrics = metrics_collector.get_metric_history("scraping.completed", minutes=60)

            last_scraping = None
            if recent_products:
                last_scraping = max(p.last_scraped_at for p in recent_products).isoformat()

            return {
                "healthy": len(active_retailers) > 0,
                "active_retailers": len(active_retailers),
                "recent_products_scraped": len(recent_products),
                "last_scraping": last_scraping,
                "scraping_operations_last_hour": len(scraping_metrics),
                "message": f"Scraping system operational with {len(active_retailers)} active retailers"
            }

    except Exception as e:
        logger.error(f"Scraping system health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "message": "Scraping system check failed"
        }


async def scheduler_health_check() -> Dict[str, Any]:
    """
    Check de salud del scheduler.
    """
    try:
        from ..core.scheduler import scheduler

        # Check if scheduler is running
        is_running = scheduler.running
        job_count = len(scheduler.get_jobs())

        # Get last scraping job execution from metrics
        scraping_started_metrics = metrics_collector.get_metric_history("scraping.started", minutes=120)
        scraping_completed_metrics = metrics_collector.get_metric_history("scraping.completed", minutes=120)

        last_execution = None
        if scraping_started_metrics:
            last_execution = scraping_started_metrics[-1].timestamp.isoformat()

        return {
            "healthy": is_running and job_count > 0,
            "scheduler_running": is_running,
            "active_jobs": job_count,
            "last_execution": last_execution,
            "executions_last_2_hours": len(scraping_started_metrics),
            "completions_last_2_hours": len(scraping_completed_metrics),
            "message": f"Scheduler {'running' if is_running else 'stopped'} with {job_count} jobs"
        }

    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "message": "Scheduler check failed"
        }


def system_resources_health_check() -> Dict[str, Any]:
    """
    Check de recursos del sistema.
    """
    try:
        import psutil
        import os

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent

        # Process info
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Health thresholds
        cpu_healthy = cpu_percent < 80
        memory_healthy = memory_percent < 85
        disk_healthy = disk_percent < 90

        overall_healthy = cpu_healthy and memory_healthy and disk_healthy

        return {
            "healthy": overall_healthy,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "process_memory_mb": round(process_memory, 2),
            "thresholds": {
                "cpu_healthy": cpu_healthy,
                "memory_healthy": memory_healthy,
                "disk_healthy": disk_healthy
            },
            "message": "System resources within acceptable limits" if overall_healthy else "System resources stressed"
        }

    except ImportError:
        # psutil not available
        return {
            "healthy": True,
            "message": "System resources check skipped (psutil not available)"
        }
    except Exception as e:
        logger.error(f"System resources health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "message": "System resources check failed"
        }


def register_all_health_checks():
    """
    Registrar todos los health checks del sistema.
    """
    logger.info("Registering health checks...")

    health_checker.register_check("database", database_health_check)
    health_checker.register_check("cache", cache_health_check)
    health_checker.register_check("scraping_system", scraping_system_health_check)
    health_checker.register_check("scheduler", scheduler_health_check)
    health_checker.register_check("system_resources", system_resources_health_check)

    logger.info("All health checks registered successfully")