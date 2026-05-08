from gantry.db import (
    getRedisCacheRepo,
    getSessionManager,
    getRedisConnectionPool,
)
from gantry.management.project import getProjectRepository
from gantry.shared.logging.logger import getLogger

from .services import ApiKeyService
from .settings import getApiKeysSettings
from .repositories import ApiKeyRepository

from functools import lru_cache

from limits.aio import storage


@lru_cache(1)
def getApiKeyRepository():
    return ApiKeyRepository(getRedisCacheRepo())


@lru_cache(1)
def getApiKeyService():
    """Get singleton ApiKeyService instance."""
    apikeys_settings = getApiKeysSettings()

    return ApiKeyService(
        config={
            "key_secret": apikeys_settings.secret.get_secret_value(),
            "api_key_secret_length": apikeys_settings.secret_length,
        },
        logger=getLogger(),
        api_key_repo=getApiKeyRepository(),
        project_repo=getProjectRepository(),
        permissions=list(apikeys_settings.permissions),
        session_manager=getSessionManager(),
        limits_storage=storage.RedisStorage(
            "redis://",
            implementation="redispy",
            # They don't pay much attention to this eh
            connection_pool=getRedisConnectionPool(),  # type: ignore
        ),
    )
