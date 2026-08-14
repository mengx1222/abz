"""Phase 6 — Monitoring & Logging Enhancement.

Provides:
- AppMetrics: singleton metrics collector (thread-safe counters)
- RequestLoggingMiddleware: per-request structured logging
- get_app_info(): convenience helper returning a snapshot dict
"""

import sys
import threading
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from structlog import get_logger

from app.core.config import settings

logger = get_logger()


# ---------------------------------------------------------------------------
# AppMetrics (singleton)
# ---------------------------------------------------------------------------


class AppMetrics:
    """Thread-safe application-level metrics collector (singleton)."""

    _instance: "AppMetrics | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "AppMetrics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # double-checked
                    cls._instance = super().__new__(cls)
                    cls._instance._init_fields()
        return cls._instance

    def _init_fields(self) -> None:
        self._counter_lock = threading.Lock()
        self._request_count: int = 0
        self._error_count: int = 0
        self._last_request_time: float = 0.0
        self.start_time: float = time.time()

    # -- mutators -----------------------------------------------------------

    def increment_requests(self) -> None:
        with self._counter_lock:
            self._request_count += 1
            self._last_request_time = time.time()

    def increment_errors(self) -> None:
        with self._counter_lock:
            self._error_count += 1

    # -- accessors ----------------------------------------------------------

    @property
    def request_count(self) -> int:
        with self._counter_lock:
            return self._request_count

    @property
    def error_count(self) -> int:
        with self._counter_lock:
            return self._error_count

    @property
    def last_request_time(self) -> float:
        with self._counter_lock:
            return self._last_request_time

    def get_metrics(self) -> dict:
        """Return a snapshot of all metrics."""
        with self._counter_lock:
            return {
                "request_count": self._request_count,
                "error_count": self._error_count,
                "last_request_time": self._last_request_time,
                "start_time": self.start_time,
                "uptime_seconds": round(time.time() - self.start_time, 2),
            }


# Module-level convenience singleton
metrics = AppMetrics()


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status_code, duration_ms, request_id.

    Skips logging for /health to avoid log noise.
    Stores duration_ms on request.state for downstream use.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health endpoint to keep logs clean
        if request.url.path == "/health":
            response = await call_next(request)
            return response

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # Store on request.state for downstream middleware/handlers
        request.state.duration_ms = duration_ms

        request_id = getattr(request.state, "request_id", "-")

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )

        return response


# ---------------------------------------------------------------------------
# get_app_info
# ---------------------------------------------------------------------------


def get_app_info() -> dict:
    """Return a snapshot dict with version, env, uptime, and metrics."""
    m = metrics.get_metrics()
    return {
        "version": settings.APP_VERSION,
        "app_env": settings.APP_ENV,
        "demo_mode": settings.DEMO_MODE,
        "uptime_seconds": m["uptime_seconds"],
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "total_requests": m["request_count"],
        "total_errors": m["error_count"],
    }
