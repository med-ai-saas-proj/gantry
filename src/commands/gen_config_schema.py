from typing import Annotated
from pathlib import Path

from pydantic import Field, AliasChoices
from pydantic_settings import (
    CliApp,
    BaseSettings,
    PydanticBaseSettingsSource,
)


class GenConfigSchema(BaseSettings, cli_prog_name="gantry gen-config-schema"):
    output: Annotated[
        Path,
        Field(
            description="Output file",
            validation_alias=AliasChoices("output", "o"),
        ),
    ] = Path("config-schema.json")

    def cli_cmd(self):
        from src.settings import AppSettings

        import json

        with self.output.open("w") as f:
            schema = AppSettings.getAppSettingsType().model_json_schema()
            json.dump(schema, f, indent=2)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def runGenConfigSchema(cli_args: list[str]):
    CliApp.run(GenConfigSchema, cli_args)
