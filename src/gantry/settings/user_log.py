from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class UserLogSettings(BaseSettings):
    loki_url: Annotated[
        HttpUrl,
        Field(
            description="Loki server URL for user activity logs.",
        ),
    ] = HttpUrl("http://localhost:3100")
    service_name: Annotated[
        str,
        Field(
            description="Service name to be used in logs.",
        ),
    ]
