from gantry.settings import (
    TomlPathConfigSettingsSource,
    DotEnvPathConfigSettingsSource,
)
from gantry.commands.server import Server
from gantry.commands.server.migrate import Migrate
from gantry.commands.gen_config_schema import GenConfigSchema
from gantry.shared.consts.common_const import APP_NAME

from pydantic_settings import (
    CliApp,
    BaseSettings,
    CliSubCommand,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)


class Main(BaseSettings, cli_prog_name=APP_NAME):
    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=False,
        env_nested_delimiter="__",
        frozen=True,
        cli_implicit_flags=True,
        cli_kebab_case="no_enums",
        cli_avoid_json=True,
    )
    server: CliSubCommand[Server]
    # migrate: CliSubCommand[Migrate]
    gen_config_schema: CliSubCommand[GenConfigSchema]

    async def cli_cmd(self):
        CliApp.run_subcommand(self)

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
            settings_cls, "server.config_file", "server"
        )
        dotenv_settings = DotEnvPathConfigSettingsSource(
            settings_cls, "server.env_file", "server"
        )
        return (
            init_settings,
            env_settings,
            toml_settings,
            dotenv_settings,
            file_secret_settings,
        )


def main():
    CliApp.run(Main)


if __name__ == "__main__":
    main()
