from __future__ import annotations

from enum import StrEnum
from typing import Self, Callable, ClassVar, Annotated, final

from pydantic import Field, FilePath, AliasChoices, create_model
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class AppStage(StrEnum):
    DEV = "DEV"
    PROD = "PROD"
    STAGING = "STAGING"


class ModifiedBaseSettings(BaseSettings):
    @classmethod
    def get(cls) -> Self: ...


class _AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="__",
        # env_nested_max_split=1,
        frozen=True,
        # cli_ignore_unknown_args=True,
        cli_implicit_flags=True,
        cli_kebab_case="no_enums",
        cli_avoid_json=True,
    )
    port: int = 8080
    internal_port: int = 9000

    stage: AppStage = AppStage.DEV
    allowed_origins: list[str] = ["*"]


@final
class AppSettings:
    """Register your settings here, used to build CLI."""

    type_arr: ClassVar[dict[str, type[ModifiedBaseSettings]]] = {}
    model_type: ClassVar[type[_AppSettings] | None] = None
    model: ClassVar[_AppSettings | None] = None

    @classmethod
    def register[T: type[ModifiedBaseSettings]](
        cls, prefix: str
    ) -> Callable[[T], T]:
        """Decorator to register your settings, pls use an appropriate prefix."""

        def wrapper(setting: T) -> T:
            setting.model_config.update(
                env_prefix=f"{prefix}_",
                cli_parse_args=True,
                cli_prefix=prefix,
                cli_ignore_unknown_args=True,
                cli_implicit_flags=True,
                cli_kebab_case="no_enums",
                cli_avoid_json=True,
                frozen=True,
            )
            setting.get = lambda: getattr(cls.get(), prefix)
            cls.type_arr[prefix] = setting
            return setting

        return wrapper

    @classmethod
    def type(cls) -> type[_AppSettings]:
        # raise RuntimeError("Shit from", __file__, 80)
        if cls.model_type is None:
            Model = create_model(
                "AppSettings",
                __base__=_AppSettings,
                **cls.type_arr,
            )
            cls.model_type = Model
            return Model
        else:
            return cls.model_type

    @classmethod
    def get(cls) -> _AppSettings:
        if cls.model is None:
            cls.model = cls.type()()
        return cls.model
