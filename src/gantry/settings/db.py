from typing import Annotated

from pydantic import Field, RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    pgvector_connection_uri: Annotated[
        PostgresDsn,
        Field(
            description="PostgreSQL connection URI for the pgvector database.",
        ),
    ]
    timescale_connection_uri: Annotated[
        PostgresDsn,
        Field(
            description="PostgreSQL connection URI for TimescaleDB.",
        ),
    ]
    redis_connection_uri: Annotated[
        RedisDsn,
        Field(description="Redis connection URI for caching."),
    ]
