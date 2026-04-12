from gantry.settings import AppSettings

from .migrate import Migrate

from typing import Annotated

from pydantic import Field, FilePath, AliasChoices
from pydantic_settings import (
    CliApp,
    CliSubCommand,
    get_subcommand,
)


class Server(AppSettings):
    migrate: CliSubCommand[Migrate]

    config_file: Annotated[
        FilePath | None,
        Field(validation_alias=AliasChoices("config_file", "f")),
    ] = None
    env_file: Annotated[
        FilePath | None,
        Field(validation_alias=AliasChoices("env_file")),
    ] = None

    async def cli_cmd(self):
        AppSettings._setInstance(self)
        if get_subcommand(self, is_required=False) is not None:
            CliApp.run_subcommand(self)
            return

        from gantry.main.app import main_app, internal_app

        import asyncio

        import uvicorn

        main_server_config = uvicorn.Config(
            main_app,
            host=self.host,
            port=self.port,
            # workers=self.workers,
            log_level=self.log_level.value.lower(),
        )

        internal_server_config = uvicorn.Config(
            internal_app,
            host=self.host,
            port=self.internal_port,
            # workers=self.internal_workers,
            log_level=self.log_level.value.lower(),
        )
        main_server = uvicorn.Server(main_server_config)
        internal_server = uvicorn.Server(internal_server_config)

        await asyncio.wait(
            [
                asyncio.create_task(main_server.serve()),
                asyncio.create_task(internal_server.serve()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
