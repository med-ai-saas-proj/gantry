from src.settings import AppSettings

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


@AppSettings.register("apikey")
class ApiKeysSetting(BaseSettings):
    secret: SecretStr
    secret_length: int = Field(gt=16, default=32)


@lru_cache(1)
def getApiKeysSettings() -> ApiKeysSetting:
    return ApiKeysSetting()
