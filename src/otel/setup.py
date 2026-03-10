from .settings import (
    LogsType,
    TracesType,
    MetricsType,
    ExporterProtocol,
    getOtelSettings,
)

import logging

from opentelemetry import _logs, trace, metrics
from structlog.stdlib import BoundLogger
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
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

def setupOtel(
    service_name: str,
    service_version: str,
    logger: BoundLogger,
):
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )

    if otel_settings.traces == TracesType.otlp:
        if otel_settings.exporter_otlp_protocol == ExporterProtocol.grpc:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        elif otel_settings.exporter_otlp_protocol == ExporterProtocol.http_protobuf:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
        else:
            raise ValueError(
                f"Unsupported OTLP exporter protocol: {otel_settings.exporter_otlp_protocol}"
            )
        exporter = OTLPSpanExporter(
            endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
            insecure=True,
        )
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)

    if otel_settings.metrics == MetricsType.otlp:
        if otel_settings.exporter_otlp_protocol == ExporterProtocol.grpc:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
        elif otel_settings.exporter_otlp_protocol == ExporterProtocol.http_protobuf:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )
        else:
            raise ValueError(
                f"Unsupported OTLP exporter protocol: {otel_settings.exporter_otlp_protocol}"
            )

        metric_exporter = OTLPMetricExporter(
            endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
            insecure=True,
        )
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(metric_exporter)
            ],
        )
        metrics.set_meter_provider(meter_provider)
    elif otel_settings.metrics == MetricsType.prometheus:
        from prometheus_client import start_http_server
        from opentelemetry.exporter.prometheus import PrometheusMetricReader

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[PrometheusMetricReader()],
        )
        metrics.set_meter_provider(meter_provider)
        start_http_server(port=otel_settings.prometheus_port, addr="0.0.0.0")

    if otel_settings.logs == LogsType.otlp:
        if otel_settings.exporter_otlp_protocol == ExporterProtocol.grpc:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter,
            )
        elif otel_settings.exporter_otlp_protocol == ExporterProtocol.http_protobuf:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter,
            )
        else:
            raise ValueError(
                f"Unsupported OTLP exporter protocol: {otel_settings.exporter_otlp_protocol}"
            )

        exporter = OTLPLogExporter(
            endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
            insecure=True,
        )
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        _logs.set_logger_provider(logger_provider)

        handler = LoggingHandler(
            level=logging.NOTSET, logger_provider=logger_provider
        )
        logging.getLogger().addHandler(handler)  # root logger
        logging.getLogger("uvicorn").addHandler(handler)  # uvicorn logger

    logger.info(f"OpenTelemetry initialized for service: {service_name}")

    HTTPXClientInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    SystemMetricsInstrumentor().instrument()

    logger.info("OpenTelemetry instrumentation completed.")
