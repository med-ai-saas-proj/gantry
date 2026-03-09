from functools import lru_cache

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class OtelSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="otel_", case_sensitive=False)

    exporter_otlp_endpoint: HttpUrl


@lru_cache(1)
def getOtelSettings() -> OtelSettings:
    return OtelSettings()  # type: ignore
