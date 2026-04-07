from src.settings import AppSettings, ModifiedBaseSettings

from enum import Enum

from pydantic import HttpUrl


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


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"
    pass


@AppSettings.register("log")
class LoggingSettings(ModifiedBaseSettings):
    level: LogLevel = LogLevel.INFO

    exporter_otlp_endpoint: HttpUrl = HttpUrl("http://localhost:4317")
    exporter_otlp_protocol: ExporterProtocol = ExporterProtocol.grpc

    traces: TracesType = TracesType.disabled
    metrics: MetricsType = MetricsType.disabled

    prometheus_port: int = 9000

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


def getOtelSettings() -> LoggingSettings:
    return LoggingSettings.get()
