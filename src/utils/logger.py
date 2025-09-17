import logging
import time
import orjson
import structlog

from src.utils.request_id import RequestIdUtils
from src.consts.env import EnvConsts


def orjson_renderer(_, __, event_dict):
    return orjson.dumps(event_dict).decode()


def ms_timestamper(_, __, event_dict):
    event_dict["timestamp"] = time.time_ns() // 1_000_000
    return event_dict


def request_ider(_, __, event_dict):
    event_dict["requestId"] = RequestIdUtils.get()
    return event_dict


def configure_default_logging(
    env, logger: logging.Logger
) -> structlog.stdlib.BoundLogger:
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        ms_timestamper,
        request_ider,
    ]
    processors = pre_chain
    is_dev = env.lower() in ["dev", "local"]
    min_level = logging.DEBUG if is_dev else logging.INFO
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(min_level)

    if env.lower() in ["prod", "dev"]:
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


LOGGER = configure_default_logging(EnvConsts.STAGE, logging.getLogger("core"))
