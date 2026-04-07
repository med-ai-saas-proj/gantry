from src.settings import AppSettings, ModifiedBaseSettings

from pydantic import Field, HttpUrl


@AppSettings.register("auth")
class AuthSetting(ModifiedBaseSettings):
    server_url: HttpUrl = Field(HttpUrl("http://localhost:8000/"))
    client_id: str = Field("example_client")
    realm_name: str = Field("example_realm")


def getAuthSettings():
    return AuthSetting.get()
