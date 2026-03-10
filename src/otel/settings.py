from enum import Enum
from functools import lru_cache

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class TracesType(str, Enum):
    otlp = "otlp"
    disabled = "disabled"

class MetricsType(str, Enum):
    otlp = "otlp"
    prometheus = "prometheus"
    disabled = "disabled"

class LogsType(str, Enum):
    otlp = "otlp"
    disabled = "disabled"

class ExporterProtocol(str, Enum):
    grpc = "grpc"
    http_protobuf = "http/protobuf"


class OtelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="otel_", case_sensitive=False)

    exporter_otlp_endpoint: HttpUrl = "http://localhost:4317"
    exporter_otlp_protocol: ExporterProtocol = ExporterProtocol.grpc

    traces: TracesType = "otlp"
    metrics: MetricsType = "otlp"
    logs: LogsType = "otlp"

    prometheus_port: int = 8001

    # OTEL defaults envvars
    # Traces
    # - :envvar:`OTEL_BSP_SCHEDULE_DELAY`
    # - :envvar:`OTEL_BSP_MAX_QUEUE_SIZE`
    # - :envvar:`OTEL_BSP_MAX_EXPORT_BATCH_SIZE`
    # - :envvar:`OTEL_BSP_EXPORT_TIMEOUT`
    # Metrics
    # -: envvar:`OTEL_METRIC_EXPORT_TIMEOUT`
    # -: envvar:`OTEL_METRIC_EXPORT_INTERVAL`
    # Logs
    # -: envvar:`OTEL_BLRP_SCHEDULE_DELAY`
    # -: envvar:`OTEL_BLRP_MAX_QUEUE_SIZE`
    # -: envvar:`OTEL_BLRP_MAX_EXPORT_BATCH_SIZE`
    # -: envvar:`OTEL_BLRP_EXPORT_TIMEOUT


@lru_cache(1)
def getOtelSettings() -> OtelSettings:
    return OtelSettings()  # type: ignore
