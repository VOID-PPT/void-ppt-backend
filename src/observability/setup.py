"""Observability wiring: OpenTelemetry + structlog.

When OTEL_EXPORTER_OTLP_ENDPOINT is unset, all exporters become no-ops so
local development needs zero configuration. In production the endpoint points
at Grafana Cloud's OTLP endpoint (free tier).
"""

import logging

import structlog
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config import settings

_OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
logger = structlog.get_logger(__name__)

_initialized = False


def setup_observability(app: object) -> None:
    """Initialize logging, tracing, and metrics exactly once.

    Called from the FastAPI lifespan. Safe to call repeatedly (idempotent).
    """
    global _initialized
    if _initialized:
        return

    resource = Resource.create(
        {
            "service.name": settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    if endpoint:
        _setup_tracing(resource, endpoint)
        _setup_metrics(resource, endpoint)
        _setup_otel_logging(resource, endpoint)

    _setup_structlog()
    _initialized = True


def _setup_tracing(resource: Resource, endpoint: str) -> None:
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)


def _setup_metrics(resource: Resource, endpoint: str) -> None:
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint),
        export_interval_millis=30_000,
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))


def _setup_otel_logging(resource: Resource, endpoint: str) -> None:
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint)))
    set_logger_provider(provider)
    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    logging.getLogger().addHandler(handler)


def _setup_structlog() -> None:
    """JSON structured logs to stdout; Fly.io/Render ship these for free."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
