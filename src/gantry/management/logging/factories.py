"""Factory functions for creating service instances."""

from gantry.shared.logging.logger import getLogger

from .services import LogQueryService
from .settings import getLoggingSettings

from functools import lru_cache

import httpx


@lru_cache(1)
def getLogQueryService() -> LogQueryService:
    """Get a singleton instance of LogQueryService."""
    logging_settings = getLoggingSettings()
    http_client = httpx.AsyncClient(
        base_url=str(logging_settings.loki_url), timeout=600
    )
    return LogQueryService(http_client, getLogger())
