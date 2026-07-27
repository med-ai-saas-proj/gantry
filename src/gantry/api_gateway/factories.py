from gantry.db import (
    getRedisConnectionPool,
)
from gantry.shared.logging.logger import getLogger

from .service import ApiGatewayService
from .settings import getApiGatewaySettings

from functools import lru_cache

from limits.aio import storage


@lru_cache(1)
def getApiGatewayService() -> ApiGatewayService:
    return ApiGatewayService(
        getLogger(),
        getApiGatewaySettings().routes,
        storage.RedisStorage(
            "redis://",
            implementation="redispy",
            # They don't pay much attention to this eh
            connection_pool=getRedisConnectionPool(),  # type: ignore
        ),
    )
