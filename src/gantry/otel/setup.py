from gantry.settings.observability import (
    LogsType,
    TracesType,
    MetricsType,
    ExporterProtocol,
)

from .settings import (
    getOtelSettings,
)

from importlib import import_module

from opentelemetry import _logs, trace, metrics
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.system_metrics import (
    SystemMetricsInstrumentor,
)


otel_settings = getOtelSettings()

_OTLP_MODULES = {
    ExporterProtocol.grpc: "opentelemetry.exporter.otlp.proto.grpc",
    ExporterProtocol.http_protobuf: "opentelemetry.exporter.otlp.proto.http",
}


def _otlp_exporter(suffix: str):
    """Import an OTLP exporter class based on the configured protocol."""
    protocol = otel_settings.exporter_otlp_protocol
    base = _OTLP_MODULES.get(protocol)
    if base is None:
        raise ValueError(f"Unsupported OTLP exporter protocol: {protocol}")
    mod = import_module(f"{base}.{suffix}")
    cls_name = suffix.rsplit(".", 1)[-1]
    # Module names like "trace_exporter" -> class "OTLPSpanExporter"
    # We just grab the single public OTLP* class from the module
    for attr in dir(mod):
        if attr.startswith("OTLP") and attr.endswith("Exporter"):
            return getattr(mod, attr)
    raise ImportError(f"No OTLP*Exporter class found in {base}.{cls_name}")


def _setup_traces(resource: Resource):
    if otel_settings.traces != TracesType.otlp:
        return
    ExporterCls = _otlp_exporter("trace_exporter")
    span_exporter = ExporterCls(
        endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
        insecure=True,
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)


def _setup_metrics(resource: Resource):
    if otel_settings.metrics == MetricsType.otlp:
        ExporterCls = _otlp_exporter("metric_exporter")
        metric_exporter = ExporterCls(
            endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
            insecure=True,
        )
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PeriodicExportingMetricReader(metric_exporter)],
        )
        metrics.set_meter_provider(meter_provider)
    elif otel_settings.metrics == MetricsType.prometheus:
        from opentelemetry.exporter.prometheus import (
            PrometheusMetricReader,
        )

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PrometheusMetricReader()],
        )
        metrics.set_meter_provider(meter_provider)


def _setup_logs(resource: Resource):
    if otel_settings.logs != LogsType.otlp:
        return
    ExporterCls = _otlp_exporter("_log_exporter")
    log_exporter = ExporterCls(
        endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
        insecure=True,
    )
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(log_exporter)
    )
    _logs.set_logger_provider(logger_provider)


def setupOtel(
    service_name: str,
    service_version: str,
):
    """Initialize OpenTelemetry traces, metrics, and logs."""
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )

    _setup_traces(resource)
    _setup_metrics(resource)
    _setup_logs(resource)

    HTTPXClientInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument()
