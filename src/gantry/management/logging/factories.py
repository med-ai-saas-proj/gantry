"""Factory functions for creating service instances."""

from .services import LogQueryService
from .settings import getLoggingSettings

from functools import lru_cache

import httpx


@lru_cache(1)
def getLogQueryService() -> LogQueryService:
    """Get a singleton instance of LogQueryService."""
    logging_settings = getLoggingSettings()
    http_client = httpx.Client(base_url=str(logging_settings.loki_url))
    return LogQueryService(http_client)
