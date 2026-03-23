from enum import StrEnum
from typing import Callable, ClassVar, NamedTuple, final
from functools import lru_cache

from pydantic import create_model
from pydantic.main import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class AppStage(StrEnum):
    DEV = "DEV"
    PROD = "PROD"
    STAGING = "STAGING"


class _AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="_",
        env_nested_max_split=1,
        frozen=True,
    )
    port: int = 8080
    internal_port: int = 9000

    stage: AppStage = AppStage.DEV
    debug: bool = False
    allowed_origins: str = "*"

    app_name: str = "Med-AI-SaaS"
    app_version: str = "1.0.0"


@final
class AppSettings:
    """Register your settings here, used to build CLI."""

    type_arr: ClassVar[dict[str, type[BaseSettings]]] = {}

    @classmethod
    def register[T: type[BaseSettings]](cls, prefix: str) -> Callable[[T], T]:
        """Decorator to register your settings, pls use an appropriate prefix."""

        def wrapper(setting: T) -> T:
            setting.model_config.update(
                env_prefix=f"{prefix}_",
                cli_parse_args=True,
                cli_prefix=prefix,
                cli_ignore_unknown_args=True,
                frozen=True,
            )
            cls.type_arr[prefix] = setting
            return setting

        return wrapper

    @classmethod
    @lru_cache(1)
    def getAppSettingsType(cls) -> type[_AppSettings]:
        Model = create_model(
            "TMP",
            __base__=_AppSettings,
            field_definitions=cls.type_arr.items(),
        )
        return Model

    @classmethod
    @lru_cache(1)
    def getAppSettings(cls) -> _AppSettings:
        return cls.getAppSettingsType()()


def getAppSettings():
    return AppSettings.getAppSettings()
