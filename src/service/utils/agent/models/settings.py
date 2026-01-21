from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="agent_", case_sensitive=False)
    grog_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


@lru_cache(1)
def getModelsSettings() -> ModelsSettings:
    return ModelsSettings()
