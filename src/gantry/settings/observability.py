from enum import Enum

from pydantic import HttpUrl
from pydantic_settings import BaseSettings


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


class ObservabilitySettings(BaseSettings):
    exporter_otlp_endpoint: HttpUrl = HttpUrl("http://localhost:4317")
    exporter_otlp_protocol: ExporterProtocol = ExporterProtocol.grpc

    traces: TracesType = TracesType.disabled
    metrics: MetricsType = MetricsType.disabled
    logs: LogsType = LogsType.disabled

    prometheus_port: int = 9000
