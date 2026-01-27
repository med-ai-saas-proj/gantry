from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="models_settings_", case_sensitive=False
    )
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


@lru_cache(1)
def getModelsSettings() -> ModelsSettings:
    return ModelsSettings()
