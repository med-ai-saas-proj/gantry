from .settings import AuthSetting, getAuthSettings
from .services.users import UserService
from .services.api_keys import ApiKeyService

from typing import Annotated
from functools import lru_cache

from fastapi import Depends


@lru_cache(1)
def getUserService():
    auth_settings = getAuthSettings()
    return UserService(
        config={
            "secret_key": auth_settings.api_key_secret.get_secret_value(),
            "algorithm": "HS256",
            "access_token_expire_minutes": auth_settings.access_token_expire_minutes,
        }
    )


@lru_cache(1)
def getAPIKeyService():
    auth_settings = getAuthSettings()
    return ApiKeyService(
        config={
            "key_secret": auth_settings.api_key_secret.get_secret_value(),
            "api_key_secret_length": auth_settings.api_key_secret_length,
            "expiration_days": auth_settings.api_key_expire_days,
        }
    )
