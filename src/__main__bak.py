from src.main import app, mainMainMain
from src.logging import getLogger
from src.settings import AppSettings

import os
import json
from typing import Any, Annotated
from pathlib import Path

from typer import Typer
from pydantic import Field, FilePath, BaseModel, AliasChoices
from pydantic.fields import FieldInfo
from pydantic_settings import (
    CliApp,
    BaseSettings,
    CliSubCommand,
    SettingsConfigDict,
    DotEnvSettingsSource,
    TomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)


print("OK")

app = Typer(
    name="gantry",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="This is not gonna help",
    epilog="I got some spare time",
    short_help="",
)


class _TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        try:
            path = self.current_state.get("server", {}).get("config_fle", None)
        except:
            path = None
        if path is not None:
            return TomlConfigSettingsSource(self.settings_cls, path)()
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False


class _DotEnvConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        try:
            path = self.current_state.get("server", {}).get("env_file", None)
        except:
            path = None
        if path is not None:
            return DotEnvSettingsSource(self.settings_cls, path)()
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False


class Server(AppSettings.getAppSettingsType()):
    def cli_cmd(self):
        # Args parsing is done
        # Setup logging
        getLogger().info("Logger configured")


class GenConfigSchema(BaseModel):
    path: Annotated[FilePath, Field()] = Path("config-schema.json")

    def cli_cmd(self):
        schema = AppSettings.getAppSettingsType().model_json_schema()

        with open(self.path, "w") as f:
            json.dump(schema, f, indent=2)


class Main(BaseSettings):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="__",
        # env_nested_max_split=1,
        frozen=True,
        # cli_ignore_unknown_args=True,
        cli_avoid_json=True,
        cli_implicit_flags=True,
        cli_kebab_case="no_enums",
    )

    server: CliSubCommand[Server]
    gen_config_schema: CliSubCommand[GenConfigSchema]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml_settings = _TomlConfigSettingsSource(settings_cls)
        dotenv_settings = _DotEnvConfigSettingsSource(settings_cls)
        print("SHITTY2")
        return (
            init_settings,
            env_settings,
            toml_settings,
            dotenv_settings,
            file_secret_settings,
        )

    def cli_cmd(self):
        print("Shit ass")
        CliApp.run_subcommand(self)


if __name__ == "__main__":
    print(os.getenv("DB_POSTGRES_CONNECTION_URI"))
    CliApp.run(Main)
