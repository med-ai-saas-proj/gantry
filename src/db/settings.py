from src.settings import AppSettings

from functools import lru_cache

from pydantic import RedisDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


@AppSettings.register("db")
class DBSettings(BaseSettings):
    postgres_connection_uri: PostgresDsn
    redis_connection_uri: RedisDsn


@lru_cache(1)
def getDBSettings():
    return DBSettings()  # type: ignore
