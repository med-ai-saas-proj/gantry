from src.main import app, mainMainMain
from src.logging import getLogger
from src.settings import AppSettings

import os
import json
from typing import Annotated
from pathlib import Path

from pydantic import Field, FilePath, BaseModel
from pydantic_settings import CliApp, CliSubCommand


print("OK")


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


class Main(BaseModel):
    server: CliSubCommand[Server]
    gen_config_schema: CliSubCommand[GenConfigSchema]

    def cli_cmd(self):
        CliApp.run_subcommand(self)


if __name__ == "__main__":
    print(os.getenv("DB_POSTGRES_CONNECTION_URI"))
    CliApp.run(Main)
