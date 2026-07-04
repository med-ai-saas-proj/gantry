from typing import Annotated

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class KeycloakSettings(BaseSettings):
    server_url: Annotated[
        HttpUrl,
        Field(
            description=(
                "Keycloak base URL reachable by the backend. This is also "
                "used as the fallback public URL when public_server_url is "
                "not configured."
            ),
        ),
    ]
    public_server_url: Annotated[
        HttpUrl | None,
        Field(
            description=(
                "Public Keycloak base URL exposed to browsers and used by "
                "OpenAPI OAuth flows."
            ),
        ),
    ] = None
    issuer_url: Annotated[
        HttpUrl | None,
        Field(
            description=(
                "Expected JWT issuer URL. Configure this when Keycloak tokens "
                "use a public hostname that differs from server_url."
            ),
        ),
    ] = None
    jwks_url: Annotated[
        HttpUrl | None,
        Field(
            description=(
                "JWKS URL used by the backend to fetch signing keys. Configure "
                "this when issuer_url is public but keys should be fetched "
                "over the cluster/internal network."
            ),
        ),
    ] = None
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
