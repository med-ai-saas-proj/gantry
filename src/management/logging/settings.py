from src.settings import AppSettings

from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


@AppSettings.register("logging")
class LoggingSetting(BaseSettings):
    loki_url: HttpUrl = Field(HttpUrl("http://localhost:3100"))


@lru_cache(1)
def getLoggingSettings() -> LoggingSetting:
    return LoggingSetting()
