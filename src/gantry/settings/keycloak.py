from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class KeycloakSettings(BaseSettings):
    server_url: Annotated[
        HttpUrl,
        Field(description="Keycloak server base URL."),
    ]
    realm_name: Annotated[
        str,
        Field(description="Keycloak realm name."),
    ]
    service_client_id: Annotated[
        str,
        Field(
            description="Service account client id for Keycloak Admin API calls.",
        ),
    ]
    service_client_secret: Annotated[
        str,
        Field(
            description="Service account client secret for Keycloak Admin API calls.",
        ),
    ]
