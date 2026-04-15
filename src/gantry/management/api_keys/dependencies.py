from gantry.settings import AppStage, getAppSettings

from .entities import ApiKeyInfo
from .services import InvalidAPIKey
from .factories import ApiKeyService, getApiKeyService
from .permissions import registerPermissions

import json
import uuid
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
    registerPermissions(permissions)
    app_settings = getAppSettings()

    async def get_api_key(
        request: Request,
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        user_info = await api_key_service.verifyApiKey(api_key, permissions)
        api_key_info = user_info.unwrap()
        _inject_api_key_context_headers(request, api_key_info)
        return api_key_info

    async def mock_get_api_key(
        request: Request,
        api_key: Annotated[str, Security(api_key_header)],
        api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    ) -> ApiKeyInfo:
        if api_key == "bypass_key":
            api_key_info = ApiKeyInfo(
                api_key_id=0,
                api_key_uuid=str(uuid.UUID(int=0)),
                user_id="test_user",
                project_id=0,
                project_uuid=str(uuid.UUID(int=0)),
                org_id="test_org1",
                organization_uuid="test_org1",
                project_uid=str(uuid.UUID(int=0)),
                hashed_key="mock_hashed_key",
                permissions=permissions,
                rpm_limit_organization=-1,
                rpm_limit_project=-1,
                spending_limit_organization=-1,
                spending_limit_project=-1,
            )
            _inject_api_key_context_headers(request, api_key_info)
            return api_key_info
        raise InvalidAPIKey()

    if app_settings.stage == AppStage.DEV:
        # If mock_auth is enabled, bypass all auth checks and return a dummy ApiKeyInfo
        return mock_get_api_key
    return get_api_key


async def getApiKeyInfo(
    request: Request,
    api_key: Annotated[str, Security(api_key_header)],
    api_key_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
):
    """Dependency to get API key info without permission checks."""

    app_settings = getAppSettings()

    if app_settings.stage == AppStage.DEV:
        if api_key == "bypass_key":
            api_key_info = ApiKeyInfo(
                api_key_id=0,
                api_key_uuid=str(uuid.UUID(int=0)),
                user_id="test_user",
                project_id=0,
                project_uuid=str(uuid.UUID(int=0)),
                org_id="test_org1",
                organization_uuid="test_org1",
                project_uid=str(uuid.UUID(int=0)),
                hashed_key="mock_hashed_key",
                permissions=[],
                rpm_limit_organization=-1,
                rpm_limit_project=-1,
                spending_limit_organization=-1,
                spending_limit_project=-1,
            )
            _inject_api_key_context_headers(request, api_key_info)
            return api_key_info
        raise InvalidAPIKey()

    user_info = await api_key_service.parseApiKey(api_key)
    api_key_info = user_info.unwrap()
    _inject_api_key_context_headers(request, api_key_info)
    return api_key_info
