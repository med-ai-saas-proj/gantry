"""Authentication and authorization dependencies for FastAPI routes."""

from ..entities.auth_info import AuthInfo, APIKeyInfo
from ..services.factories import (
    UserService,
    ApiKeyService,
    getUserService,
    getAPIKeyService,
)

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)


def get_current_user(
    token: Annotated[str, Security(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> AuthInfo:
    """Dependency to get the current authenticated user from the access token."""
    return user_service.getUserInfoFromAccessToken(token).unwrap()


def required_permission(permission: list[str]):
    """Dependency to verify the API key and required permissions."""

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
    ) -> APIKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permission)
        return user_info.unwrap()

    return get_api_key
