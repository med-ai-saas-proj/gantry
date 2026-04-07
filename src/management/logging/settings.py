from src.settings import AppSettings, ModifiedBaseSettings

from pydantic import HttpUrl


@AppSettings.register("logging")
class LoggingSetting(ModifiedBaseSettings):
    loki_url: HttpUrl = HttpUrl("http://localhost:3100")


def getLoggingSettings():
    return LoggingSetting.get()
