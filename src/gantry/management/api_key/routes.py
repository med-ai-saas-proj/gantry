"""Management routes for project-scoped API keys."""

from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.management.project.factories import (
    ProjectService,
    getProjectService,
)
from gantry.management.project.permissions import ProjectPermission

from .dtos import (
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyWriteRequest,
    ApiKeyCreateResponse,
    ApiKeyPermissionCatalogResponse,
)
from .factories import ApiKeyService, getApiKeyService

from typing import Annotated

from fastapi import Body, Path, Query, Depends, Response, APIRouter


apikey_router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    include_in_schema=True,
)


@apikey_router.get(
    "/permissions", response_model=ApiKeyPermissionCatalogResponse
)
async def getApiKeyPermissions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> ApiKeyPermissionCatalogResponse:
    """List all runtime permissions that can be assigned to API keys."""
    _ = user_info
    return apikey_service.getPermissionCatalog()


@apikey_router.get("", response_model=ApiKeyListResponse)
async def getApiKeys(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_uuid: Annotated[str, Query(..., min_length=1, alias="project_id")],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyListResponse:
    """List API keys belonging to one project."""
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_READ,
    )
    authz_res.unwrap()
    result = await apikey_service.getApiKeys(project_uuid=project_uuid)
    return result.unwrap()


@apikey_router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def createApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_uuid: Annotated[str, Query(..., min_length=1, alias="project_id")],
    input_data: Annotated[ApiKeyWriteRequest, Body()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyCreateResponse:
    """Create a new API key in one project."""
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()
    result = await apikey_service.createApiKey(
        actor_user_id=user_info["id"],
        project_uuid=project_uuid,
        name=input_data.name,
        description=input_data.description,
        permissions=input_data.permissions,
    )
    return result.unwrap()


@apikey_router.get("/{api_key_uuid}", response_model=ApiKeyResponse)
async def getApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Get one API key by uuid after project permission authorization."""
    project_uuid_res = await apikey_service.getApiKeyProjectUuid(api_key_uuid)
    project_uuid = project_uuid_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_READ,
    )
    authz_res.unwrap()

    result = await apikey_service.getApiKey(api_key_uuid)
    return result.unwrap()


@apikey_router.put("/{api_key_uuid}", response_model=ApiKeyResponse)
async def updateApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    input_data: Annotated[ApiKeyWriteRequest, Body()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Update one API key after project write permission authorization."""
    project_uuid_res = await apikey_service.getApiKeyProjectUuid(api_key_uuid)
    project_uuid = project_uuid_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.updateApiKey(
        api_key_uuid=api_key_uuid,
        name=input_data.name,
        description=input_data.description,
        permissions=input_data.permissions,
    )
    return result.unwrap()


@apikey_router.post("/{api_key_uuid}/disable", response_model=ApiKeyResponse)
async def disableApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Disable one API key after project write permission authorization."""
    project_uuid_res = await apikey_service.getApiKeyProjectUuid(api_key_uuid)
    project_uuid = project_uuid_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.setApiKeyDisabled(
        api_key_uuid=api_key_uuid,
        disabled=True,
    )
    return result.unwrap()


@apikey_router.post("/{api_key_uuid}/enable", response_model=ApiKeyResponse)
async def enableApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Enable one API key after project write permission authorization."""
    project_uuid_res = await apikey_service.getApiKeyProjectUuid(api_key_uuid)
    project_uuid = project_uuid_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.setApiKeyDisabled(
        api_key_uuid=api_key_uuid,
        disabled=False,
    )
    return result.unwrap()


@apikey_router.delete("/{api_key_uuid}")
async def deleteApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> Response:
    """Delete one API key after project write permission authorization."""
    project_uuid_res = await apikey_service.getApiKeyProjectUuid(api_key_uuid)
    project_uuid = project_uuid_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_uuid,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.deleteApiKey(api_key_uuid)
    result.unwrap()
    return Response(status_code=200)
