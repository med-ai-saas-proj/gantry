from src.shared.utils.logger import getLogger

from .entities import UserInfo
from .settings import getAuthSettings
from .factories import KeycloakService, getKeycloakService

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer


auth_settings = getAuthSettings()
server_url_str = auth_settings.server_url.encoded_string()
realm_name = auth_settings.realm_name

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/token",
    authorizationUrl=f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/auth",
    refreshUrl=f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/token",
)


async def getUserInfo(
    token: Annotated[str, Security(oauth_2_scheme)],
    keycloak_service: Annotated[KeycloakService, Depends(getKeycloakService)],
) -> UserInfo:
    return keycloak_service.verify_token(token).unwrap()
