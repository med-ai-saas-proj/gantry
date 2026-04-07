from src.shared.utils import request_id_utils

from .settings import getOtelSettings

import time
from functools import lru_cache

import orjson
import structlog
from opentelemetry import trace
from structlog.stdlib import BoundLogger
from structlog.processors import CallsiteParameter


def addOTELSpans(_, __, event_dict):
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


def orjsonRenderer(_, __, event_dict):
    return orjson.dumps(event_dict).decode()


def msTimestamper(_, __, event_dict):
    event_dict["timestamp"] = time.time_ns() // 1_000_000
    return event_dict


def requestIder(_, __, event_dict):
    event_dict["requestId"] = request_id_utils.get()
    return event_dict


@lru_cache(1)
def getLogger() -> structlog.stdlib.BoundLogger:
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
        # structlog.processors.StackInfoRenderer(),
        structlog.processors.dict_tracebacks,
        msTimestamper,
        requestIder,
        addOTELSpans,
    ]
    processors = pre_chain + [orjsonRenderer]

    return structlog.wrap_logger(
        None,
        processors=processors,
        context_class=dict,
        wrapper_class=structlog.make_filtering_bound_logger(
            getOtelSettings().level.value
        ),
        logger_factory=structlog.BytesLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def getServiceLogger(
    org_id: str,
    project_id: str | None = None,
) -> BoundLogger:
    if project_id:
        return getLogger().bind(projectId=project_id, orgId=org_id)
    return getLogger().bind(orgId=org_id)
