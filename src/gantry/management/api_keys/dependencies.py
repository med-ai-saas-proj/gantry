from gantry.settings import AppStage, getAppSettings
from gantry.management.api_keys.services import InvalidAPIKey

from .entities import ApiKeyInfo
from .factories import ApiKeyService, getApiKeyService
from .permissions import registerPermissions

import uuid
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
    app_settings = getAppSettings()

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permissions)
        return user_info.unwrap()

    async def mock_get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        if api_key == "bypass_key":
            return ApiKeyInfo(
                api_key_id=0,
                user_id="test_user",
                project_id=0,
                org_id="test_org1",
                project_uid=str(uuid.UUID(int=0)),
                hashed_key="mock_hashed_key",
            )
        raise InvalidAPIKey()

    if app_settings.stage == AppStage.DEV:
        # If mock_auth is enabled, bypass all auth checks and return a dummy ApiKeyInfo
        return mock_get_api_key
    return get_api_key


def getApiKeyInfo(
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
):
    """Dependency to get API key info without permission checks."""

    app_settings = getAppSettings()

    async def get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.parseApiKey(api_key)
        return user_info.unwrap()

    async def mock_get_api_key(
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        if api_key == "bypass_key":
            return ApiKeyInfo(
                api_key_id=0,
                user_id="test_user",
                project_id=0,
                org_id="test_org1",
                project_uid=str(uuid.UUID(int=0)),
                hashed_key="mock_hashed_key",
            )
        raise InvalidAPIKey()

    if app_settings.stage == AppStage.DEV:
        # If mock_auth is enabled, bypass all auth checks and return a dummy ApiKeyInfo
        return mock_get_api_key
    return get_api_key
