# from src.commands.server import RunServer
# from src.commands.gen_config_schema import RunGenConfigSchema

# from pydantic_settings import (
#     CliApp,
#     BaseSettings,
#     CliSubCommand,
#     CliUnknownArgs,
#     SettingsConfigDict,
# )


# class MainCliApp(BaseSettings):
#     model_config = SettingsConfigDict(
#         cli_parse_args=True,
#         cli_ignore_unknown_args=True,
#         cli_kebab_case="no_enums",
#         cli_prog_name="gantry",
#         cli_avoid_json=True,
#     )

#     server: CliSubCommand[RunServer]
#     gen_config_schema: CliSubCommand[RunGenConfigSchema]
#     unknown_args: CliUnknownArgs

#     def cli_cmd(self):
#         CliApp.run_subcommand(self)

import typer


app = typer.Typer(
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    rich_help_panel=None,
    name="gantry",
    help="This is not gonna help",
    suggest_commands=True,
)

context_settings = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
    "help_option_names": [],
}


@app.command(
    "gen-config-schema",
    context_settings=context_settings,
)
def genConfigSchema(ctx: typer.Context):
    from src.commands.gen_config_schema import runGenConfigSchema

    runGenConfigSchema(ctx.args)


@app.command(
    "server",
    context_settings=context_settings,
)
def server(ctx: typer.Context):
    from src.commands.server import runServer

    runServer(ctx.args)


if __name__ == "__main__":
    # CliApp.run(MainCliApp)
    app()
