from src.settings import AppSettings, ModifiedBaseSettings

from pydantic import Field, SecretStr


@AppSettings.register("apikeys")
class ApiKeysSetting(ModifiedBaseSettings):
    secret: SecretStr
    secret_length: int = Field(gt=16, default=32)


def getApiKeysSettings() -> ApiKeysSetting:
    return ApiKeysSetting.get()
