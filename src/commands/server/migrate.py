from typing import Annotated
from pathlib import Path

from pydantic import Field, FilePath, AliasChoices
from pydantic_settings import (
    BaseSettings,
)


class Migrate(BaseSettings):
    def cli_cmd(self):
        from src.settings import AppSettings

        print(AppSettings.get())
