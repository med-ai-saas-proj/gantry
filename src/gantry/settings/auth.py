from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    client_id: Annotated[
        str,
        Field(description="Keycloak OIDC client ID."),
    ] = "example_client"
    admin_client_id: Annotated[
        str,
        Field(description="Keycloak OIDC client ID for admin users."),
    ] = "example_admin_client"
