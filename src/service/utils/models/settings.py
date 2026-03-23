from src.settings import AppSettings

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


@AppSettings.register("aimodel")
class ModelsSettings(BaseSettings):
    openai_base_url: str | None = None
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


@lru_cache(1)
def getModelsSettings() -> ModelsSettings:
    return ModelsSettings()
