from enum import Enum
from typing import Annotated

from pydantic import Field, HttpUrl
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
    exporter_otlp_endpoint: Annotated[
        HttpUrl,
        Field(description="OTLP exporter endpoint URL."),
    ] = HttpUrl("http://localhost:4317")
    exporter_otlp_protocol: Annotated[
        ExporterProtocol,
        Field(description="OTLP exporter protocol (gRPC or HTTP)."),
    ] = ExporterProtocol.grpc

    traces: Annotated[
        TracesType,
        Field(description="Traces exporter type."),
    ] = TracesType.disabled
    metrics: Annotated[
        MetricsType,
        Field(description="Metrics exporter type."),
    ] = MetricsType.disabled
    logs: Annotated[
        LogsType,
        Field(description="Logs exporter type."),
    ] = LogsType.disabled

    prometheus_port: Annotated[
        int,
        Field(
            description="Port for the Prometheus metrics endpoint.",
        ),
    ] = 9000
