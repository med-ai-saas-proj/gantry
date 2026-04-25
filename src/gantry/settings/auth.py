from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    server_url: Annotated[
        HttpUrl,
        Field(description="Keycloak server base URL."),
    ] = HttpUrl("http://localhost:8000/")
    client_id: Annotated[
        str,
        Field(description="Keycloak OIDC client ID."),
    ] = "example_client"
    admin_client_id: Annotated[
        str,
        Field(description="Keycloak OIDC client ID for admin users."),
    ] = "example_admin_client"
    realm_name: Annotated[
        str,
        Field(description="Keycloak realm name."),
    ] = "example_realm"
