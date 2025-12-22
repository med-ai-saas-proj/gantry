from functools import lru_cache

from pydantic import RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_", case_sensitive=False)
    postgres_connection_uri: PostgresDsn
    redis_connection_uri: RedisDsn


@lru_cache(1)
def getDBSettings():
    return DBSettings()  # type: ignore
