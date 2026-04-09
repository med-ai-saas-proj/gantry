from src.shared.consts import common_const

import typer


app = typer.Typer(
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    rich_help_panel=None,
    name=common_const.APP_NAME,
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


@app.command("migrate", context_settings=context_settings)
def migrate(ctx: typer.Context):
    from src.commands.migrate import runMigrate

    runMigrate(ctx.args)


if __name__ == "__main__":
    # CliApp.run(MainCliApp)
    app()
