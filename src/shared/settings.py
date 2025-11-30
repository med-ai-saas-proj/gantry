from enum import StrEnum
from functools import lru_cache

from pydantic import Field, RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppStage(StrEnum):
    DEV = "DEV"
    PROD = "PROD"
    STAGING = "STAGING"


class AppSettings(BaseSettings):
    stage: AppStage = Field(AppStage.DEV)
    debug: bool = Field(False)


@lru_cache(1)
def getAppSetting():
    return AppSettings() # type: ignore
