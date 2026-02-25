import time
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import Response


class MetricsCollector:
    """Centralized metrics collection for Network Guardian AI."""

    def __init__(self) -> None:
        self.threats_detected = Counter(
            "ng_threats_detected_total",
            "Total number of threats detected",
            ["category", "risk_level"],
        )

        self.anomaly_score = Histogram(
            "ng_anomaly_score",
            "Distribution of anomaly scores",
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        self.cache_hits = Counter(
            "ng_cache_hits_total",
            "Total number of cache hits",
        )

        self.cache_misses = Counter(
            "ng_cache_misses_total",
            "Total number of cache misses",
        )

        self.gemini_api_calls = Counter(
            "ng_gemini_api_calls_total",
            "Total number of Gemini API calls",
            ["status", "model"],
        )

        self.gemini_api_latency = Histogram(
            "ng_gemini_api_latency_seconds",
            "Latency of Gemini API calls in seconds",
            ["model"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.analysis_latency = Histogram(
            "ng_analysis_latency_seconds",
            "Latency of domain analysis in seconds",
            ["source"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        self.domains_processed = Counter(
            "ng_domains_processed_total",
            "Total number of domains processed",
            ["source"],
        )

        self.active_connections = Gauge(
            "ng_active_connections",
            "Number of active WebSocket connections",
        )

        self.system_cpu_percent = Gauge(
            "ng_system_cpu_percent",
            "Current CPU usage percentage",
        )

        self.system_memory_percent = Gauge(
            "ng_system_memory_percent",
            "Current memory usage percentage",
        )

        self.system_disk_percent = Gauge(
            "ng_system_disk_percent",
            "Current disk usage percentage",
        )

        self.vector_memory_size = Gauge(
            "ng_vector_memory_size",
            "Number of embeddings stored in vector memory",
        )

        self.classifier_decisions = Counter(
            "ng_classifier_decisions_total",
            "Total classifier decisions",
            ["result"],
        )

    def record_threat(self, category: str, risk_level: str) -> None:
        """Record a detected threat."""
        self.threats_detected.labels(category=category, risk_level=risk_level).inc()

    def record_anomaly_score(self, score: float) -> None:
        """Record an anomaly score."""
        self.anomaly_score.observe(score)

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits.inc()

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses.inc()

    def record_gemini_call(self, status: str, model: str, latency: float) -> None:
        """Record a Gemini API call."""
        self.gemini_api_calls.labels(status=status, model=model).inc()
        self.gemini_api_latency.labels(model=model).observe(latency)

    @asynccontextmanager
    async def track_analysis_latency(self, source: str):
        """Context manager to track analysis latency."""
        start_time = time.time()
        yield
        latency = time.time() - start_time
        self.analysis_latency.labels(source=source).observe(latency)

    def record_domain_processed(self, source: str) -> None:
        """Record a processed domain."""
        self.domains_processed.labels(source=source).inc()

    def set_active_connections(self, count: int) -> None:
        """Set the number of active WebSocket connections."""
        self.active_connections.set(count)

    def update_system_metrics(self) -> dict:
        """Update and return system resource metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        self.system_cpu_percent.set(cpu_percent)
        self.system_memory_percent.set(memory.percent)
        self.system_disk_percent.set(disk.percent)

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }

    def set_vector_memory_size(self, size: int) -> None:
        """Set the vector memory size."""
        self.vector_memory_size.set(size)

    def record_classifier_decision(self, result: str) -> None:
        """Record a classifier decision."""
        self.classifier_decisions.labels(result=result).inc()


metrics_collector = MetricsCollector()


def setup_prometheus(app: FastAPI, port: int = 9090) -> FastAPI:
    """
    Set up Prometheus metrics on a separate FastAPI app.

    Args:
        app: The main FastAPI application
        port: Port for the metrics server (not used in-app)

    Returns:
        A new FastAPI app for metrics endpoint
    """
    metrics_app = FastAPI(title="Network Guardian AI Metrics")

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="ng_http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    @metrics_app.get("/metrics")
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint."""
        metrics_collector.update_system_metrics()
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @metrics_app.get("/health")
    async def metrics_health() -> dict:
        """Health check for metrics server."""
        return {"status": "healthy", "service": "metrics"}

    return metrics_app
