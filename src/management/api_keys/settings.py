from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiKeysSetting(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="apikeys_", case_sensitive=False
    )
    secret: SecretStr
    secret_length: int = Field(gt=16, default=32)


@lru_cache(1)
def getApiKeysSettings() -> ApiKeysSetting:
    return ApiKeysSetting()
