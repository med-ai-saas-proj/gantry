from ..settings import AuthSetting, getAuthSettings
from ..factories import (
    UserService,
    ApiKeyService,
    KeycloakService,
    getUserService,
    getAPIKeyService,
    getKeycloakService,
)
from ..entities.auth_info import AuthInfo

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer


_settings = getAuthSettings()
_token_url = f"{_settings.keycloak_server_url}/realms/{_settings.keycloak_realm}/protocol/openid-connect/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=_token_url)


api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)


async def get_current_user(
    token: Annotated[str, Security(oauth2_scheme)],
    settings: Annotated[AuthSetting, Depends(getAuthSettings)],
    keycloak_service: Annotated[KeycloakService, Depends(getKeycloakService)],
) -> AuthInfo:
    if settings.keycloak_enabled:
        return keycloak_service.verify_token(token)


def required_permission(permission: list[str]):
    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
    ):
        user_info = await api_key_service.verify_api_key(api_key, permission)
        return user_info.unwrap()

    return get_api_key
