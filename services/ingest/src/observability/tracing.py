from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, TraceIdRatioBased

from src.config import get_settings

_PROVIDER: TracerProvider | None = None


def configure_tracing() -> None:
    global _PROVIDER
    if _PROVIDER is not None:
        return

    settings = get_settings()
    if not settings.otel_enabled:
        return

    sampler = ALWAYS_ON if settings.environment == "prod" else TraceIdRatioBased(0.1)

    _PROVIDER = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.service_name,
                "deployment.environment": settings.environment,
            }
        ),
        sampler=sampler,
    )
    _PROVIDER.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True))
    )
    trace.set_tracer_provider(_PROVIDER)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def record_enrichment_attributes(span: trace.Span, indicator: dict[str, Any], upstream_url: str) -> None:
    span.set_attribute("nightjar.indicator", str(indicator))
    span.set_attribute("nightjar.upstream_url", upstream_url)
    span.set_attribute("nightjar.raw_upstream", str(indicator.get("raw_upstream", "")))
