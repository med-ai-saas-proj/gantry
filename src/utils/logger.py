import logging
import time
import orjson
import structlog

from src.consts.env import EnvConsts


def orjson_renderer(_, __, event_dict):
    return orjson.dumps(event_dict).decode()


def ms_timestamper(_, __, event_dict):
    event_dict["latencyMs"] = time.time_ns() // 1_000_000
    return event_dict


def configure_default_logging(env, logger: logging.Logger) -> structlog.stdlib.BoundLogger:
    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        ms_timestamper,
    ]
    processors = pre_chain
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    if env.lower() in ["prod", "dev"]:
        processors += [orjson_renderer]
    else:
        processors += [structlog.dev.ConsoleRenderer()]

    return structlog.wrap_logger(
        logger,
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        # logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


LOGGER = configure_default_logging(EnvConsts.STAGE, logging.getLogger("core"))
