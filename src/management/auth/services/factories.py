"""Factories for authentication services."""

from src.db.factories import getRedis, getSessionManager
from src.shared.utils.logger import getLogger

from .users import UserService
from .api_keys import ApiKeyService
from ..settings import getAuthSettings
from ..repositories.factories import (
    getUserRepository,
    getApiKeyRepository,
    getPermissionRepository,
)

from functools import lru_cache


@lru_cache(1)
def getUserService():
    """Get singleton UserService instance."""
    auth_settings = getAuthSettings()
    return UserService(
        config={
            "access_token_algorithm": "HS256",
            "access_token_expire_minutes": auth_settings.access_token_expire_minutes,
            "access_token_secret_key": auth_settings.api_key_secret.get_secret_value(),
            "refresh_token_algorithm": "HS256",
            "refresh_token_secret_key": auth_settings.refresh_token_secret.get_secret_value(),
            "refresh_token_expire_days": auth_settings.refresh_token_expire_days,
            "login_attempt_window_minutes": auth_settings.login_attempt_window_minutes,
            "max_login_attempts": auth_settings.max_login_attempts,
        },
        logger=getLogger(),
        user_repo=getUserRepository(),
        session_manager=getSessionManager(),
        redis_client=getRedis(),
    )


@lru_cache(1)
def getAPIKeyService():
    """Get singleton ApiKeyService instance."""
    auth_settings = getAuthSettings()
    return ApiKeyService(
        config={
            "key_secret": auth_settings.api_key_secret.get_secret_value(),
            "api_key_secret_length": auth_settings.api_key_secret_length,
            "expiration_days": auth_settings.api_key_expire_days,
        },
        logger=getLogger(),
        user_repo=getUserRepository(),
        api_key_repo=getApiKeyRepository(),
        permission_repo=getPermissionRepository(),
        session_manager=getSessionManager(),
    )
