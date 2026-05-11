from .entities import ApiKeyInfo
from .factories import ApiKeyService, getApiKeyService

import os
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-Api-Key",
    description="API authorization header. Put your API token here.",
)

enable_mock_auth = os.getenv("GANTRY_ENABLE_MOCK_AUTH", "").lower() in {
    "1",
    "true",
    "yes",
}


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

    from gantry.settings import AppStage, getAppSettings

    from .services import InvalidAPIKey

    import uuid

    app_settings = getAppSettings()
    if app_settings.stage == AppStage.DEV and enable_mock_auth:

        async def mock_api_key(
            request: Request,
            api_key: Annotated[str | None, Security(api_key_header)],
        ) -> ApiKeyInfo:
            if api_key == "bypass_key":
                return {
                    "api_key_id": 0,
                    "api_key_uuid": str(uuid.UUID(int=0)),
                    "user_uuid": "test_user",
                    "hashed_key": "bypass_hashed_key",
                    "project_id": 0,
                    "project_uuid": str(uuid.UUID(int=0)),
                    "organization_uuid": "test_org1",
                    "permissions": permissions,
                    "rpm_limit_organization": 1000000,
                    "rpm_limit_project": 1000000,
                    "spending_limit_organization": 1000000,
                    "spending_limit_project": 1000000,
                }
            raise InvalidAPIKey()

        return mock_api_key

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
