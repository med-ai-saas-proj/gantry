from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class ApiKeysSettings(BaseSettings):
    secret: SecretStr
    secret_length: Annotated[int, Field(gt=16, default=32)]
