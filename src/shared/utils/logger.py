from . import request_id_utils
from ..settings import AppStage, getAppSetting

import time
import logging
from functools import lru_cache

import orjson
import structlog
from structlog.stdlib import BoundLogger
from structlog.processors import CallsiteParameter


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
