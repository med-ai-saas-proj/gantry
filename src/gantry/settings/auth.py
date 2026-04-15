from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    server_url: HttpUrl = HttpUrl("http://localhost:8000/")
    client_id: str = "example_client"
    realm_name: str = "example_realm"
