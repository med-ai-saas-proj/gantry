from __future__ import annotations

from gantry.settings.rag import RagSettings

from .db import DBSettings
from .auth import AuthSettings
from .utils import TomlPathConfigSettingsSource, DotEnvPathConfigSettingsSource
from .billing import BillingSettings
from .api_keys import ApiKeysSettings
from .user_log import UserLogSettings
from .api_gateway import ApiGatewaySettings
from .conversation import ConversationSettings
from .file_storage import ObjectStorageSettings
from .organization import OrgSettings
from .observability import ObservabilitySettings

from enum import StrEnum
from typing import Self, Literal, ClassVar, Annotated

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
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
    __instance: ClassVar[Self | None] = None
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

    rag: RagSettings
    stage: Annotated[
        AppStage,
        Field(description="Application deployment stage."),
    ] = AppStage.DEV
    allowed_origins: Annotated[
        list[str] | Literal["*"],
        Field(description="CORS allowed origins. Use '*' to allow all."),
    ] = "*"
    host: Annotated[
        str,
        Field(description="Host address to bind the server to."),
    ] = "127.0.0.1"
    port: Annotated[
        int,
        Field(description="Port for the public-facing main application."),
    ] = 8000
    internal_port: Annotated[
        int,
        Field(description="Port for the internal API and metrics."),
    ] = 9000
    log_level: Annotated[
        LogLevel,
        Field(description="Minimum log level for the application."),
    ] = LogLevel.WARNING

    db: Annotated[
        DBSettings,
        Field(description="Database connection settings."),
    ]
    apikey: Annotated[
        ApiKeysSettings,
        Field(description="API key generation and validation settings."),
    ]
    auth: Annotated[
        AuthSettings,
        Field(description="Keycloak authentication settings."),
    ]
    billing: Annotated[
        BillingSettings,
        Field(description="Stripe billing and invoice settings."),
    ]
    user_log: Annotated[
        UserLogSettings,
        Field(description="User activity log settings."),
    ]
    conversation: Annotated[
        ConversationSettings,
        Field(description="Conversation caching settings."),
    ]
    file_storage: Annotated[
        ObjectStorageSettings,
        Field(description="S3-compatible object storage settings."),
    ]
    organization: Annotated[
        OrgSettings,
        Field(description="Organization management settings."),
    ]
    observability: Annotated[
        ObservabilitySettings,
        Field(description="OpenTelemetry observability settings."),
    ]
    api_gateway: Annotated[
        ApiGatewaySettings,
        Field(description="API gateway routing and permissions."),
    ]

    @classmethod
    def get(cls) -> Self:
        if cls.__instance is None:
            # raise RuntimeError("AppSettings is loaded before initialize")
            from gantry.__main__ import Main

            import sys

            tmp = sys.argv
            sys.argv = ["gantry", "server"]
            main = Main()
            cls.__instance = main.server
            sys.argv = tmp
        return cls.__instance

    @classmethod
    def _setInstance(cls, val: Self):
        cls.__instance = val


def getAppSettings():
    return AppSettings.get()
