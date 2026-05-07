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


def _inject_api_key_context_headers(
    request: Request,
    api_key_info: ApiKeyInfo,
) -> None:
    headers = request.headers.mutablecopy()
    headers["X-Organization-UUID"] = api_key_info["organization_uuid"]
    headers["X-Project-UUID"] = api_key_info["project_uuid"]
    headers["X-API-Key-UUID"] = api_key_info["api_key_uuid"]
    headers["X-Permissions"] = json.dumps(api_key_info["permissions"])
    headers["X-RPM-Limit-Organization"] = str(
        api_key_info["rpm_limit_organization"]
    )
    headers["X-RPM-Limit-Project"] = str(api_key_info["rpm_limit_project"])
    headers["X-Spending-Limit-Organization"] = str(
        api_key_info["spending_limit_organization"]
    )
    headers["X-Spending-Limit-Project"] = str(
        api_key_info["spending_limit_project"]
    )
    request._headers = headers
    request.scope["headers"] = headers.raw
    request.state.api_key_info = api_key_info


def requiredPermissions(permissions: list[str]):
    """Dependency to verify the API key and create required permissions."""

    async def get_api_key(
        request: Request,
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permissions)
        api_key_info = user_info.unwrap()
        _inject_api_key_context_headers(request, api_key_info)
        return api_key_info

    return get_api_key


async def getApiKeyInfo(
    request: Request,
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> ApiKeyInfo:
    """Dependency to get API key info without permission checks."""
    user_info = await api_key_service.parseApiKey(api_key)
    api_key_info = user_info.unwrap()
    _inject_api_key_context_headers(request, api_key_info)
    return api_key_info
