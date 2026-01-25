from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .services import ApiKeyService
from .permission_service import PermissionService
from .settings import getApiKeysSettings
from .repositories import ApiKeyRepository, PermissionRepository

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
        permission_repo=PermissionRepository(),
        session_manager=getSessionManager(),
    )


@lru_cache(1)
def getPermissionService():
    """Get singleton PermissionService instance."""
    return PermissionService(
        logger=getLogger(),
        permission_repo=PermissionRepository(),
        session_manager=getSessionManager(),
    )
