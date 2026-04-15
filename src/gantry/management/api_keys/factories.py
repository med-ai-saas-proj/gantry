from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger
from gantry.management.project.repositories import ProjectRepository

from .services import ApiKeyService
from .settings import getApiKeysSettings
from .repositories import ApiKeyRepository

from functools import lru_cache


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
        api_key_repo=ApiKeyRepository(),
        project_repo=ProjectRepository(),
        session_manager=getSessionManager(),
        redis=getRedis(),
    )
