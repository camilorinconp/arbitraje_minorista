# backend/services/metrics.py

import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Valor de métrica con timestamp."""
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Collector de métricas del sistema.
    """

    def __init__(self, max_history_minutes: int = 60):
        self.max_history = timedelta(minutes=max_history_minutes)
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1, tags: Optional[Dict[str, str]] = None):
        """Incrementar contador."""
        with self._lock:
            key = self._get_metric_key(name, tags)
            self._counters[key] += value
            self._add_to_history(name, value, tags)

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Establecer valor de gauge."""
        with self._lock:
            key = self._get_metric_key(name, tags)
            self._gauges[key] = value
            self._add_to_history(name, value, tags)

    def record_timing(self, name: str, duration_seconds: float, tags: Optional[Dict[str, str]] = None):
        """Registrar tiempo de operación."""
        with self._lock:
            self._add_to_history(f"{name}.duration", duration_seconds, tags)

    def _get_metric_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Generar clave única para métrica con tags."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"

    def _add_to_history(self, name: str, value: float, tags: Optional[Dict[str, str]]):
        """Agregar valor al historial."""
        metric = MetricValue(
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self._metrics[name].append(metric)

    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Obtener valor de contador."""
        with self._lock:
            key = self._get_metric_key(name, tags)
            return self._counters.get(key, 0)

    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Obtener valor de gauge."""
        with self._lock:
            key = self._get_metric_key(name, tags)
            return self._gauges.get(key, 0)

    def get_metric_history(self, name: str, minutes: int = 10) -> List[MetricValue]:
        """Obtener historial de métrica."""
        with self._lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            history = self._metrics.get(name, deque())
            return [m for m in history if m.timestamp >= cutoff]

    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtener todas las métricas actuales."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timestamp": datetime.now().isoformat()
            }

    def cleanup_old_metrics(self):
        """Limpiar métricas antiguas."""
        with self._lock:
            cutoff = datetime.now() - self.max_history
            for name, history in self._metrics.items():
                # Remover elementos antiguos
                while history and history[0].timestamp < cutoff:
                    history.popleft()


class PerformanceTracker:
    """
    Tracker de performance para operaciones específicas.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    async def track_operation(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager para trackear duración de operaciones."""
        return OperationTracker(self.metrics, operation_name, tags)


class OperationTracker:
    """Context manager para tracking de operaciones."""

    def __init__(self, metrics: MetricsCollector, operation_name: str, tags: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        self.metrics.increment_counter(f"{self.operation_name}.started", 1, self.tags)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        # Registrar duración
        self.metrics.record_timing(self.operation_name, duration, self.tags)

        # Incrementar contador de éxito/fallo
        if exc_type is None:
            self.metrics.increment_counter(f"{self.operation_name}.success", 1, self.tags)
        else:
            self.metrics.increment_counter(f"{self.operation_name}.error", 1, self.tags)
            # Registrar tipo de error
            error_tags = {**self.tags, "error_type": exc_type.__name__}
            self.metrics.increment_counter(f"{self.operation_name}.error_by_type", 1, error_tags)


class HealthChecker:
    """
    Verificador de salud del sistema.
    """

    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}

    def register_check(self, name: str, check_func: callable):
        """Registrar check de salud."""
        self.checks[name] = check_func
        logger.info(f"Health check registered: {name}")

    async def run_all_checks(self) -> Dict[str, Any]:
        """Ejecutar todos los checks de salud."""
        results = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        overall_healthy = True

        for name, check_func in self.checks.items():
            try:
                start_time = time.time()

                if asyncio.iscoroutinefunction(check_func):
                    check_result = await check_func()
                else:
                    check_result = check_func()

                duration = time.time() - start_time

                result = {
                    "status": "healthy" if check_result.get("healthy", True) else "unhealthy",
                    "duration_ms": round(duration * 1000, 2),
                    **check_result
                }

                if not check_result.get("healthy", True):
                    overall_healthy = False

            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}", exc_info=True)
                result = {
                    "status": "unhealthy",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                overall_healthy = False

            results["checks"][name] = result
            self.last_results[name] = result

        results["status"] = "healthy" if overall_healthy else "unhealthy"
        return results

    async def get_check_result(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtener resultado de un check específico."""
        return self.last_results.get(name)


# Instancias globales
metrics_collector = MetricsCollector()
performance_tracker = PerformanceTracker(metrics_collector)
health_checker = HealthChecker()


# Task para limpieza periódica de métricas
async def periodic_metrics_cleanup():
    """Limpiar métricas antiguas cada 10 minutos."""
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutos
            metrics_collector.cleanup_old_metrics()
            logger.debug("Metrics cleanup completed")
        except Exception as e:
            logger.error(f"Error in metrics cleanup: {e}", exc_info=True)