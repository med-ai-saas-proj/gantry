from src.settings import (
    TomlPathConfigSettingsSource,
    DotEnvPathConfigSettingsSource,
)
from src.commands.server import Server
from src.commands.gen_config_schema import GenConfigSchema
from src.shared.consts.common_const import APP_NAME

from pydantic import Field
from pydantic_settings import (
    CliApp,
    BaseSettings,
    CliSubCommand,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    get_subcommand,
)


class Main(Server, cli_prog_name=APP_NAME):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="__",
        frozen=True,
        cli_implicit_flags=True,
        cli_kebab_case="no_enums",
        cli_avoid_json=True,
    )
    gen_config_schema: CliSubCommand[GenConfigSchema]

    async def cli_cmd(self):
        if get_subcommand(self, is_required=False) is not None:
            CliApp.run_subcommand(self)
            return
        return await super().cli_cmd()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml_settings = TomlPathConfigSettingsSource(
            settings_cls,
            "gantry_config_file",
        )
        dotenv_settings = DotEnvPathConfigSettingsSource(
            settings_cls,
            "gantry_env_file",
        )
        return (
            init_settings,
            env_settings,
            toml_settings,
            dotenv_settings,
            file_secret_settings,
        )


if __name__ == "__main__":
    CliApp.run(Main)
