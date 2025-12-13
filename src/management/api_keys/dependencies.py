from .entities import ApiKeyInfo
from .factories import ApiKeyService, getApiKeyService

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)


def requiredPermission(permission: list[str]):
    """Dependency to verify the API key and create required permissions."""

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permission)
        return user_info.unwrap()

    return get_api_key
