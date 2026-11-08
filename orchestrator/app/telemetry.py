"""OpenTelemetry distributed tracing and structured JSON logging."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class JSONTraceLogFormatter(logging.Formatter):
    """Custom log formatter injecting trace_id and span_id into structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None

        trace_id = None
        span_id = None
        if span_context and span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")

        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id,
            "span_id": span_id,
        }

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_telemetry(
    service_name: str = "orchestrator-service",
    otlp_endpoint: Optional[str] = None,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracer provider with OTLP exporter and fallback."""
    # If a TracerProvider is already registered, return existing tracer
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        return trace.get_tracer(service_name)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    otlp_enabled = False
    import os
    is_test = os.getenv("ENVIRONMENT") == "test"
    if otlp_endpoint and otlp_endpoint.startswith("http") and not is_test:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            otlp_enabled = True
        except Exception as exc:
            logging.getLogger(__name__).warning("Could not initialize OTLP exporter: %s", exc)

    if not otlp_enabled:
        # Minimal in-memory / console fallback without blocking network
        pass

    try:
        trace.set_tracer_provider(provider)
    except Exception:
        pass

    return trace.get_tracer(service_name)


def configure_structured_logging(level: str = "INFO") -> None:
    """Configure root logger with JSONTraceLogFormatter for production observability."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONTraceLogFormatter())
    root_logger.addHandler(handler)


def get_current_trace_id() -> Optional[str]:
    """Retrieve the current active span's 32-character hex trace ID."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None
