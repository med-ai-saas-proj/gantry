"""Management routes for project-scoped API keys."""

from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.management.project.factories import ProjectService, getProjectService
from src.management.project.permissions import ProjectPermission

from .dtos import (
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyWriteRequest,
    ApiKeyCreateResponse,
    ApiKeyPermissionAuditResponse,
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


@apikey_router.get(
    "/permissions/audit", response_model=ApiKeyPermissionAuditResponse
)
async def auditApiKeyPermissions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> ApiKeyPermissionAuditResponse:
    """Audit mismatches between runtime and stored API key permissions."""
    _ = user_info
    result = await apikey_service.auditPermissions()
    return result


@apikey_router.get("", response_model=ApiKeyListResponse)
async def getApiKeys(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_id: Annotated[str, Query(..., min_length=1, alias="project_id")],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyListResponse:
    """List API keys belonging to one project."""
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_READ,
    )
    authz_res.unwrap()
    result = await apikey_service.getApiKeys(project_uuid=project_id)
    return result.unwrap()


@apikey_router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def createApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_id: Annotated[str, Query(..., min_length=1, alias="project_id")],
    input_data: Annotated[ApiKeyWriteRequest, Body()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyCreateResponse:
    """Create a new API key in one project."""
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()
    result = await apikey_service.createApiKey(
        actor_user_id=user_info["id"],
        project_uuid=project_id,
        name=input_data.name,
        description=input_data.description,
        permissions=input_data.permissions,
    )
    return result.unwrap()


@apikey_router.get("/{apikey_id}", response_model=ApiKeyResponse)
async def getApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_id: Annotated[int, Path()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Get one API key by id after project permission authorization."""
    project_id_res = await apikey_service.getApiKeyProjectId(apikey_id)
    project_id = project_id_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_READ,
    )
    authz_res.unwrap()

    result = await apikey_service.getApiKey(apikey_id)
    return result.unwrap()


@apikey_router.put("/{apikey_id}", response_model=ApiKeyResponse)
async def updateApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_id: Annotated[int, Path()],
    input_data: Annotated[ApiKeyWriteRequest, Body()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Update one API key after project write permission authorization."""
    project_id_res = await apikey_service.getApiKeyProjectId(apikey_id)
    project_id = project_id_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.updateApiKey(
        api_key_id=apikey_id,
        name=input_data.name,
        description=input_data.description,
        permissions=input_data.permissions,
    )
    return result.unwrap()


@apikey_router.post("/{apikey_id}/disable", response_model=ApiKeyResponse)
async def disableApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_id: Annotated[int, Path()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Disable one API key after project write permission authorization."""
    project_id_res = await apikey_service.getApiKeyProjectId(apikey_id)
    project_id = project_id_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.setApiKeyDisabled(
        api_key_id=apikey_id,
        disabled=True,
    )
    return result.unwrap()


@apikey_router.post("/{apikey_id}/enable", response_model=ApiKeyResponse)
async def enableApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_id: Annotated[int, Path()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ApiKeyResponse:
    """Enable one API key after project write permission authorization."""
    project_id_res = await apikey_service.getApiKeyProjectId(apikey_id)
    project_id = project_id_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.setApiKeyDisabled(
        api_key_id=apikey_id,
        disabled=False,
    )
    return result.unwrap()


@apikey_router.delete("/{apikey_id}")
async def deleteApiKey(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    apikey_id: Annotated[int, Path()],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> Response:
    """Delete one API key after project write permission authorization."""
    project_id_res = await apikey_service.getApiKeyProjectId(apikey_id)
    project_id = project_id_res.unwrap()
    authz_res = await project_service.authorizeProjectPermission(
        project_uuid=project_id,
        user_id=user_info["id"],
        required=ProjectPermission.APIKEY_WRITE,
    )
    authz_res.unwrap()

    result = await apikey_service.deleteApiKey(apikey_id)
    result.unwrap()
    return Response(status_code=200)
