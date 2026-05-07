from typing import Annotated
from datetime import timedelta

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
    cache_ttl: Annotated[
        timedelta | None,
        Field(description="Cache time-to-live, None mean never expire"),
    ] = timedelta(hours=1)
