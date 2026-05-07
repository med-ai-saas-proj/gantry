from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class ApiKeyPermission(BaseSettings):
    id: Annotated[
        str,
        Field(description="Unique permission identifier."),
    ]
    name: Annotated[
        str,
        Field(description="Human-readable permission name."),
    ]
    description: Annotated[
        str,
        Field(
            description="Explanation of what this permission grants.",
        ),
    ]


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
    permissions: Annotated[
        list[ApiKeyPermission],
        Field(description="Available API key permissions."),
    ] = []
