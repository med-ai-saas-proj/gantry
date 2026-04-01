from .entities import ApiKeyInfo
from .factories import ApiKeyService, getApiKeyService
from .permissions import registerPermissions

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)


def requiredPermissions(permissions: list[str]):
    """Dependency to verify the API key and create required permissions."""
    registerPermissions(permissions)

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permissions)
        return user_info.unwrap()

    return get_api_key


async def getApiKeyInfo(
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> ApiKeyInfo:
    user_info = await api_key_service.parseApiKey(api_key)
    return user_info.unwrap()
