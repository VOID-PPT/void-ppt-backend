"""Request-scoped middleware: request ID propagation and RED timing metrics."""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER = "X-Request-ID"

_http_duration_histogram = None  # set lazily in setup() to avoid import cycles
_request_total = None
_logger = structlog.get_logger(__name__)


def record_http_metrics() -> None:
    """Lazily create metric instruments (idempotent)."""
    global _http_duration_histogram, _request_total
    if _http_duration_histogram is not None:
        return
    from opentelemetry import metrics as otel_metrics

    # Force proxy -> real meter resolution after SDK setup
    otel_metrics.get_meter_provider()
    from src.observability.setup import meter

    _http_duration_histogram = meter.create_histogram(
        name="http_server_request_seconds",
        unit="s",
        description="HTTP request duration by route/method/status",
    )
    _request_total = meter.create_counter(
        name="http_server_requests_total",
        description="HTTP requests by route/method/status",
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID, binds it into every log line, and records RED metrics."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        record_http_metrics()
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            _logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
            )
            raise
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        duration = time.perf_counter() - start
        route = request.scope.get("route")
        route_template = getattr(route, "path", request.url.path)

        if _http_duration_histogram is not None:
            _http_duration_histogram.record(
                duration,
                {
                    "http.request.method": request.method,
                    "http.route": route_template,
                    "http.response.status_code": response.status_code,
                },
            )
            _request_total.add(
                1,
                {
                    "http.request.method": request.method,
                    "http.route": route_template,
                    "http.response.status_code": response.status_code,
                },
            )

        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
