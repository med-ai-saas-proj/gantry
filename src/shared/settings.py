from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppStage(StrEnum):
    DEV = "DEV"
    PROD = "PROD"
    STAGING = "STAGING"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)
    stage: AppStage = Field(AppStage.DEV)
    debug: bool = Field(False)
    allowed_origins: str = Field("*")

    app_name: str = Field("Med-AI-SaaS")
    app_version: str = Field("1.0.0")
    openapi_json_path: str = Field("/docs/openapi.json")
    docs_url: str = Field("/docs")


@lru_cache(1)
def getAppSetting():
    return AppSettings()
