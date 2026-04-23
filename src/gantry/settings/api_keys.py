from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class ApiKeysSettings(BaseSettings):
    secret: Annotated[
        SecretStr,
        Field(
            description="Secret key used for API key HMAC signing.",
        ),
    ]
    secret_length: Annotated[
        int,
        Field(
            gt=16,
            description="Length of generated API key secrets.",
        ),
    ] = 32
