from typing import Annotated
from pathlib import Path

from pydantic import Field, AliasChoices
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)


class GenConfigSchema(BaseSettings):
    output: Annotated[
        Path,
        Field(
            description="Output file",
            validation_alias=AliasChoices("output", "o"),
        ),
    ] = Path("config-schema.json")

    def cli_cmd(self):
        from gantry.settings import AppSettings

        import json

        with self.output.open("w") as f:
            schema = AppSettings.model_json_schema()
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
