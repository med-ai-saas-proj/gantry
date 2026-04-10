from __future__ import annotations

from .db import DBSettings
from .auth import AuthSettings
from .utils import TomlPathConfigSettingsSource, DotEnvPathConfigSettingsSource
from .billing import BillingSourceSettings
from .api_keys import ApiKeysSettings
from .user_log import UserLogSettings
from .conversation import ConversationSettings
from .file_storage import ObjectStorageSettings
from .organization import OrgSettings
from .observability import ObservabilitySettings

import os
from enum import StrEnum
from typing import Self, Literal, ClassVar, Annotated

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)


class AppStage(StrEnum):
    DEV = "DEV"
    PROD = "PROD"
    STAGING = "STAGING"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class AppSettings(BaseSettings):
    __instance: ClassVar[AppSettings | None] = None
    model_config = SettingsConfigDict(
        # cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="__",
        frozen=True,
        cli_implicit_flags=True,
        cli_kebab_case="no_enums",
        cli_avoid_json=True,
        cli_ignore_unknown_args=True,
    )

    stage: AppStage = AppStage.DEV
    allowed_origins: list[str] | Literal["*"] = "*"
    host: str = "127.0.0.1"
    port: int = 8000
    internal_port: int = 9000
    workers: Annotated[int, Field(gt=0)] = 1
    internal_workers: Annotated[int, Field(gt=0)] = 1
    log_level: LogLevel = LogLevel.WARNING

    db: DBSettings
    apikey: ApiKeysSettings
    auth: AuthSettings
    billing: BillingSourceSettings
    user_log: UserLogSettings
    conversation: ConversationSettings
    file_storage: ObjectStorageSettings
    organization: OrgSettings
    observability: ObservabilitySettings

    @classmethod
    def get(cls) -> Self:
        return cls.__instance

    @classmethod
    def _setInstance(cls, val: Self):
        cls.__instance = val


def getAppSettings():
    return AppSettings.get()
