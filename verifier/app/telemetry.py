"""OpenTelemetry distributed tracing for Verifier Service."""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(
    service_name: str = "verifier-service",
    otlp_endpoint: Optional[str] = None,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracer for verifier service."""
    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider):
        return trace.get_tracer(service_name)

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    is_test = os.getenv("ENVIRONMENT") == "test"
    if otlp_endpoint and otlp_endpoint.startswith("http") and not is_test:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception:
            pass

    try:
        trace.set_tracer_provider(provider)
    except Exception:
        pass

    return trace.get_tracer(service_name)
