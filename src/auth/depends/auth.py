from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from ..entities.auth_info import AuthInfo
from ..factories import (
    UserService,
    ApiKeyService,
    getUserService,
    getAPIKeyService,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(
    token: Annotated[str, Security(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(getUserService)],
) -> AuthInfo:
    return user_service.getUserInfoFromAccessToken(token).unwrap()


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def required_permission(permission: list[str]):
    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getAPIKeyService)],
    ):
        return await api_key_service.verify_api_key(api_key, permission)

    return get_api_key
