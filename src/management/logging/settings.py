from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSetting(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="logging_", case_sensitive=False)
    loki_url: HttpUrl = Field(HttpUrl("http://localhost:3100"))


@lru_cache(1)
def getLoggingSettings() -> LoggingSetting:
    return LoggingSetting()
