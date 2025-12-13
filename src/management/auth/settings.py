from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="auth_", case_sensitive=False)
    server_url: HttpUrl = Field(HttpUrl("http://localhost:8000/"))
    client_id: str = Field("example_client")
    realm_name: str = Field("example_realm")


@lru_cache(1)
def getAuthSettings() -> AuthSetting:
    return AuthSetting()
