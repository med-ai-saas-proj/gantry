from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class KeycloakSettings(BaseSettings):
    server_url: Annotated[
        HttpUrl,
        Field(description="Keycloak server base URL."),
    ] = HttpUrl("http://localhost:8000/")
    realm_name: Annotated[
        str,
        Field(description="Keycloak realm name."),
    ] = "example_realm"
