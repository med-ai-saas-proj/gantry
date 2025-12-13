from src.shared.utils.logger import getLogger

from .entities import UserInfo
from .settings import getAuthSettings

from typing import Annotated

from fastapi import Depends
from keycloak import KeycloakOpenID
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


auth_settings = getAuthSettings()
keycloak_client = KeycloakOpenID(
    server_url=auth_settings.server_url.encoded_string(),
    client_id=auth_settings.client_id,
    realm_name=auth_settings.realm_name,
)

auth_bearer_scheme = HTTPBearer()


async def getUserInfo(
    credendtial: Annotated[
        HTTPAuthorizationCredentials, Depends(auth_bearer_scheme)
    ],
) -> UserInfo:
    # The token is a JWT token that can be validate using the realm's public key
    # https://www.keycloak.org/docs/25.0.6/securing_apps/index.html#validating-access-tokens
    token = credendtial.credentials
    payload = await keycloak_client.a_decode_token(token, validate=True)
    getLogger().debug("Got user info from token", payload=payload)
    return {
        "id": payload["sub"],
        "username": payload["preferred_username"],
        "email": payload["email"],
    }
