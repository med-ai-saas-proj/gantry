from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="auth_", case_sensitive=False)
    jwt_secret: SecretStr
    access_token_expire_minutes: int = Field(gt=0)
    api_key_secret: SecretStr
    api_key_secret_length: int = Field(gt=16)
    api_key_expire_days: int = Field(gt=1)


@lru_cache(1)
def getAuthSettings():
    return AuthSetting()
