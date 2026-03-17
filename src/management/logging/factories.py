"""Factory functions for creating service instances."""
import httpx

from .services import LogQueryService
from functools import lru_cache


@lru_cache(1)
def getLogQueryService() -> LogQueryService:
    """Get a singleton instance of LogQueryService."""
    http_client = httpx.Client(base_url="http://localhost:3100")
    return LogQueryService(http_client)
