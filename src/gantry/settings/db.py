from pydantic import RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    pgvector_connection_uri: PostgresDsn
    timescale_connection_uri: PostgresDsn
    redis_connection_uri: RedisDsn
