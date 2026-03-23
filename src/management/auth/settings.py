from src.settings import AppSettings

from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


AppSettings.register("auth")


class AuthSetting(BaseSettings):
    server_url: HttpUrl = Field(HttpUrl("http://localhost:8000/"))
    client_id: str = Field("example_client")
    realm_name: str = Field("example_realm")


@lru_cache(1)
def getAuthSettings() -> AuthSetting:
    return AuthSetting()
