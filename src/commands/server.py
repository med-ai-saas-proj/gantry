from src.main import mainMainMain
from src.settings import AppSettings
from src.shared.consts.common_const import APP_NAME

from typing import Any, Annotated

from pydantic import Field, FilePath, AliasChoices
from pydantic.fields import FieldInfo
from pydantic_settings import (
    CliApp,
    BaseSettings,
    DotEnvSettingsSource,
    TomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)


class _TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)

    def __call__(self) -> dict[str, Any]:
        try:
            path = self.current_state.get("config_file", None)
        except:
            path = None
        if path is not None:
            tmp = TomlConfigSettingsSource(self.settings_cls, path)()
            print(tmp, "from", __file__)
            return tmp
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
            path = self.current_state.get("env_file", None)
        except:
            path = None
        if path is not None:
            tmp = DotEnvSettingsSource(self.settings_cls, path)()
            print(tmp, "from", __file__)
            return tmp
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, "", False


class Server(AppSettings.type(), cli_prog_name=f"{APP_NAME} server"):
    config_file: Annotated[
        FilePath | None,
        Field(validation_alias=AliasChoices("config_file", "f")),
    ] = None
    env_file: Annotated[
        FilePath | None,
        Field(validation_alias=AliasChoices("env_file")),
    ] = None

    async def cli_cmd(self):
        # Args parsing is done
        # Setup logging
        logger = setupLogger(self)
        # print("Just pretendinng that the server just ran")
        pass

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
        return (
            init_settings,
            env_settings,
            toml_settings,
            dotenv_settings,
            file_secret_settings,
        )


def runServer(cli_args: list[str]):
    CliApp.run(Server, cli_args)
