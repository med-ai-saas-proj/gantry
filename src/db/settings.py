from src.settings import AppSettings, ModifiedBaseSettings

from pydantic import RedisDsn, PostgresDsn


@AppSettings.register("db")
class DBSettings(ModifiedBaseSettings):
    postgres_connection_uri: PostgresDsn
    redis_connection_uri: RedisDsn


def getDBSettings():
    return DBSettings.get()
