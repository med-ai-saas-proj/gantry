from gantry.settings import AppStage, getAppSettings

from .entities import ApiKeyInfo
from .services import InvalidAPIKey
from .factories import ApiKeyService, getApiKeyService

import json
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)


def requiredPermissions(permissions: list[str]):
    """Dependency to verify the API key and create required permissions."""

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permissions)
        api_key_info = user_info.unwrap()
        (await api_key_service.rateLimit(api_key_info)).unwrap()
        # _inject_api_key_context_headers(request, api_key_info)
        return api_key_info

    return get_api_key


async def getApiKeyInfo(
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> ApiKeyInfo:
    """Dependency to get API key info without permission checks."""
    user_info = await api_key_service.parseApiKey(api_key)
    api_key_info = user_info.unwrap()
    (await api_key_service.rateLimit(api_key_info)).unwrap()
    # _inject_api_key_context_headers(request, api_key_info)
    return api_key_info
