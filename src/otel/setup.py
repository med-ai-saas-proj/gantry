from .settings import getOtelSettings

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
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)


otel_settings = getOtelSettings()


def setupOtel(
        service_name: str,
        service_version: str,
        logger: BoundLogger
):
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
                    insecure=True,
                )
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=otel_settings.exporter_otlp_endpoint.encoded_string(),
                insecure=True,
            )
        )
    )
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
