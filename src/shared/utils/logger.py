from . import request_id_utils
from ..settings import AppStage, getAppSetting

import time
import logging
from functools import lru_cache

import orjson
import structlog
from opentelemetry import trace
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
    settings = getAppSetting()
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
    min_level = logging.DEBUG if settings.debug else logging.INFO
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(min_level)

    if settings.stage == AppStage.PROD:
        processors += [orjson_renderer]
    else:
        processors += [structlog.dev.ConsoleRenderer()]

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
    return configure_default_logging(logging.getLogger("core"))


LOGGER: BoundLogger = getLogger()
