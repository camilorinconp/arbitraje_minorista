# backend/routes/observability.py

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from ..services.metrics import metrics_collector, health_checker
from ..services.cache import app_cache
from ..services.logging_config import set_correlation_id
from ..services.rate_limiter import limiter

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/health", response_model=Dict[str, Any])
@limiter.limit("200/minute")
@limiter.limit("5000/hour")
async def health_check(request: Request):
    """
    Endpoint de health check del sistema.
    """
    try:
        result = await health_checker.run_all_checks()

        # Set HTTP status based on health
        if result["status"] != "healthy":
            raise HTTPException(status_code=503, detail=result)

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "message": "Health check system failed"
            }
        )


@router.get("/health/{check_name}", response_model=Dict[str, Any])
async def individual_health_check(check_name: str):
    """
    Endpoint para un health check específico.
    """
    result = await health_checker.get_check_result(check_name)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")

    if result.get("status") != "healthy":
        raise HTTPException(status_code=503, detail=result)

    return result


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """
    Endpoint para obtener todas las métricas del sistema.
    """
    try:
        metrics = metrics_collector.get_all_metrics()

        # Add cache metrics
        cache_stats = await app_cache.get_stats()
        metrics["cache"] = cache_stats

        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")


@router.get("/metrics/{metric_name}/history", response_model=List[Dict[str, Any]])
async def get_metric_history(
    metric_name: str,
    minutes: int = Query(default=10, ge=1, le=60, description="Minutes of history to retrieve")
):
    """
    Endpoint para obtener el historial de una métrica específica.
    """
    try:
        history = metrics_collector.get_metric_history(metric_name, minutes)

        return [
            {
                "value": entry.value,
                "timestamp": entry.timestamp.isoformat(),
                "tags": entry.tags
            }
            for entry in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metric history: {str(e)}")


@router.get("/metrics/counter/{counter_name}", response_model=Dict[str, Any])
async def get_counter(counter_name: str, tags: Optional[str] = Query(None, description="Tags in format key1=value1,key2=value2")):
    """
    Endpoint para obtener el valor de un contador específico.
    """
    try:
        # Parse tags if provided
        parsed_tags = None
        if tags:
            parsed_tags = {}
            for tag_pair in tags.split(","):
                if "=" in tag_pair:
                    key, value = tag_pair.split("=", 1)
                    parsed_tags[key.strip()] = value.strip()

        value = metrics_collector.get_counter(counter_name, parsed_tags)

        return {
            "counter_name": counter_name,
            "value": value,
            "tags": parsed_tags,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving counter: {str(e)}")


@router.get("/metrics/gauge/{gauge_name}", response_model=Dict[str, Any])
async def get_gauge(gauge_name: str, tags: Optional[str] = Query(None, description="Tags in format key1=value1,key2=value2")):
    """
    Endpoint para obtener el valor de un gauge específico.
    """
    try:
        # Parse tags if provided
        parsed_tags = None
        if tags:
            parsed_tags = {}
            for tag_pair in tags.split(","):
                if "=" in tag_pair:
                    key, value = tag_pair.split("=", 1)
                    parsed_tags[key.strip()] = value.strip()

        value = metrics_collector.get_gauge(gauge_name, parsed_tags)

        return {
            "gauge_name": gauge_name,
            "value": value,
            "tags": parsed_tags,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving gauge: {str(e)}")


@router.post("/correlation-id", response_model=Dict[str, str])
async def set_correlation_id_endpoint(correlation_id: Optional[str] = None):
    """
    Endpoint para establecer correlation ID para debugging.
    """
    try:
        corr_id = set_correlation_id(correlation_id)
        return {
            "correlation_id": corr_id,
            "message": "Correlation ID set successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting correlation ID: {str(e)}")


@router.get("/system-info", response_model=Dict[str, Any])
async def get_system_info():
    """
    Endpoint para información general del sistema.
    """
    try:
        import psutil
        import os
        from datetime import timedelta

        # Process info
        process = psutil.Process(os.getpid())

        # System info
        system_info = {
            "process": {
                "pid": os.getpid(),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            },
            "system": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                "uptime": str(timedelta(seconds=int(time.time() - psutil.boot_time())))
            },
            "application": {
                "name": "Arbitraje Minorista API",
                "version": "0.1.0",
                "timestamp": datetime.now().isoformat()
            }
        }

        return system_info

    except ImportError:
        # psutil not available
        return {
            "application": {
                "name": "Arbitraje Minorista API",
                "version": "0.1.0",
                "timestamp": datetime.now().isoformat()
            },
            "message": "Extended system info not available (psutil not installed)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system info: {str(e)}")


# Readiness and liveness probes for Kubernetes
@router.get("/ready", response_model=Dict[str, str])
async def readiness_probe():
    """
    Readiness probe para Kubernetes.
    """
    try:
        # Quick health checks for readiness
        health_result = await health_checker.run_all_checks()

        if health_result["status"] == "healthy":
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail={"status": "not ready", "details": health_result})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "not ready", "error": str(e)})


@router.get("/live", response_model=Dict[str, str])
async def liveness_probe():
    """
    Liveness probe para Kubernetes.
    """
    # Simple liveness check - if this endpoint responds, the app is alive
    return {"status": "alive", "timestamp": datetime.now().isoformat()}