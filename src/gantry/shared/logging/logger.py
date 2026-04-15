from gantry.settings import AppStage, getAppSettings
from gantry.shared.consts.common_const import APP_NAME

from ..utils import request_id_utils

import time
import logging
from functools import lru_cache

import orjson
import structlog
from opentelemetry import trace
from structlog.dev import ConsoleRenderer
from structlog.stdlib import BoundLogger
from structlog.processors import CallsiteParameter


def add_open_telemetry_spans(_, __, event_dict):
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None
        if not parent
        else format(parent.span_id, "016x"),
    }

    return event_dict


def orjson_renderer(_, __, event_dict):
    return orjson.dumps(event_dict).decode()


def ms_timestamper(_, __, event_dict):
    event_dict["timestamp"] = time.time_ns() // 1_000_000
    return event_dict


def request_ider(_, __, event_dict):
    event_dict["requestId"] = request_id_utils.get()
    return event_dict


def configure_default_logging(
    logger: logging.Logger,
) -> structlog.stdlib.BoundLogger:
    settings = getAppSettings()
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            [
                CallsiteParameter.PATHNAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        ms_timestamper,
        request_ider,
        add_open_telemetry_spans,
    ]
    processors = pre_chain
    min_level = (
        logging.DEBUG if settings.stage == AppStage.DEV else logging.INFO
    )
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(min_level)

    processors += [
        orjson_renderer if settings.stage != AppStage.DEV else ConsoleRenderer()
    ]

    return structlog.wrap_logger(
        logger,
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        # logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@lru_cache(1)
def getLogger() -> BoundLogger:
    return configure_default_logging(logging.getLogger(APP_NAME))


def getServiceLogger(
    org_id: str,
    project_id: str | None = None,
) -> BoundLogger:
    if project_id:
        return getLogger().bind(projectId=project_id, orgId=org_id)
    return getLogger().bind(orgId=org_id)
