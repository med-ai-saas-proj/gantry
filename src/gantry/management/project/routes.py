"""API routes for project management."""

from gantry.management.auth import UserInfo, getUserInfo
from gantry.management.organization import OrgPermission, requiredOrgPermission

from .dtos import (
    PaginationQuery,
    ProjectListQuery,
    ProjectInfoResponse,
    ProjectListResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    AddProjectUserRequest,
    ProjectArchiveResponse,
    ProjectSettingsResponse,
    ProjectUserListResponse,
    UpdateProjectSettingsRequest,
    ProjectUserPermissionsRequest,
    ProjectUserPermissionsResponse,
    ProjectPermissionCatalogResponse,
)
from .services import ProjectNotFoundError
from .factories import ProjectService, getProjectService
from .permissions import ALL_PERMISSIONS, ProjectPermission
from .dependencies import requiredProjectPermission

from typing import Annotated

from fastapi import Body, Path, Query, Depends, Response, APIRouter


project_router = APIRouter(prefix="/projects", tags=["projects"])


@project_router.get(
    "/permissions",
    response_model=ProjectPermissionCatalogResponse,
)
async def list_project_permissions() -> ProjectPermissionCatalogResponse:
    """Return the full project permission catalog for UI consumers."""
    return ProjectPermissionCatalogResponse(permissions=ALL_PERMISSIONS)


@project_router.get("", response_model=ProjectListResponse)
async def get_projects(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    query: Annotated[ProjectListQuery, Depends()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectListResponse:
    """List joined projects or all org projects depending on the query."""
    if query.organization:
        await requiredOrgPermission(OrgPermission.PROJECTS_GET_ALL)(user_info)
        result = await project_service.listOrgProjects(
            actor_user_id=user_info["id"],
            organization_id=query.organization,
            q=query.q,
            limit=query.limit,
            offset=query.offset,
        )
        return result.unwrap()

    result = await project_service.listUserProjects(
        actor_user_id=user_info["id"],
        q=query.q,
        limit=query.limit,
        offset=query.offset,
    )
    return result.unwrap()


@project_router.post("", response_model=ProjectInfoResponse, status_code=201)
async def create_project(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    organization: Annotated[str, Query(..., min_length=1)],
    input_data: Annotated[CreateProjectRequest, Body()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectInfoResponse:
    """Create a project inside the requested organization."""
    result = await project_service.createProject(
        actor_user_id=user_info["id"],
        organization_id=organization,
        name=input_data.name,
        description=input_data.description,
    )
    return result.unwrap()


@project_router.get("/{project_uuid}", response_model=ProjectInfoResponse)
async def get_project(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_uuid: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectInfoResponse:
    """Return one project when the actor can access it."""
    result = await project_service.getProject(
        project_uuid=project_uuid,
        actor_user_id=user_info["id"],
    )
    return result.unwrap()


@project_router.put("/{project_uuid}", response_model=ProjectInfoResponse)
async def update_project(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.SETTINGS_WRITE)),
    ],
    project_uuid: Annotated[str, Path()],
    input_data: Annotated[UpdateProjectRequest, Body()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectInfoResponse:
    """Update mutable metadata for one project."""
    result = await project_service.updateProject(
        project_uuid=project_uuid,
        name=input_data.name,
        description=input_data.description,
    )
    return result.unwrap()


@project_router.get(
    "/{project_uuid}/settings",
    response_model=ProjectSettingsResponse,
)
async def get_project_settings(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.SETTINGS_READ)),
    ],
    project_uuid: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectSettingsResponse:
    """Return project settings for one readable project."""
    _ = user_info
    result = await project_service.getProjectSettings(project_uuid)
    return result.unwrap()


@project_router.patch(
    "/{project_uuid}/settings",
    response_model=ProjectSettingsResponse,
)
async def update_project_settings(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.SETTINGS_WRITE)),
    ],
    project_uuid: Annotated[str, Path()],
    input_data: Annotated[UpdateProjectSettingsRequest, Body()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectSettingsResponse:
    """Update per-project settings such as the project RPM limit."""
    _ = user_info
    result = await project_service.updateProjectSettings(
        project_uuid=project_uuid,
        rate_limit=input_data.rate_limit,
        spending_limit=input_data.spending_limit,
        extra=input_data.extra,
    )
    return result.unwrap()


@project_router.get(
    "/{project_uuid}/users",
    response_model=ProjectUserListResponse,
)
async def get_project_users(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.USERS_GET_ALL)),
    ],
    project_uuid: Annotated[str, Path()],
    pagination: Annotated[PaginationQuery, Depends()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectUserListResponse:
    """List users currently assigned to one project."""
    result = await project_service.listProjectUsers(
        project_uuid=project_uuid,
        offset=pagination.offset,
        limit=pagination.limit,
        q=pagination.q,
    )
    return result.unwrap()


@project_router.post("/{project_uuid}/users")
async def add_project_user(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.USERS_ADD)),
    ],
    project_uuid: Annotated[str, Path()],
    input_data: Annotated[AddProjectUserRequest, Body()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> Response:
    """Add an organization member into the project."""
    result = await project_service.addUserToProject(
        project_uuid=project_uuid,
        target_user_id=input_data.user_id,
    )
    result.unwrap()
    return Response(status_code=200)


@project_router.delete("/{project_uuid}/users/{user_id}")
async def remove_project_user(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.USERS_REMOVE)),
    ],
    project_uuid: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> Response:
    """Remove one user from the project."""
    result = await project_service.removeUserFromProject(
        project_uuid=project_uuid, target_user_id=user_id
    )
    result.unwrap()
    return Response(status_code=200)


@project_router.get(
    "/{project_uuid}/users/{user_id}/permissions",
    response_model=ProjectUserPermissionsResponse,
)
async def get_project_user_permissions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    project_uuid: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectUserPermissionsResponse:
    """Return project permissions for a user, allowing self-read."""
    if user_info["id"] != user_id:
        authz_res = await project_service.authorizeProjectPermission(
            project_uuid=project_uuid,
            user_id=user_info["id"],
            required=ProjectPermission.USERS_PERMISSIONS_RW,
        )
        authz_res.unwrap()

    result = await project_service.getUserPermissions(
        project_uuid=project_uuid,
        target_user_id=user_id,
    )
    return result.unwrap()


@project_router.put(
    "/{project_uuid}/users/{user_id}/permissions",
    response_model=ProjectUserPermissionsResponse,
)
async def update_project_user_permissions(
    user_info: Annotated[
        UserInfo,
        Depends(
            requiredProjectPermission(ProjectPermission.USERS_PERMISSIONS_RW)
        ),
    ],
    project_uuid: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    input_data: Annotated[ProjectUserPermissionsRequest, Body()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectUserPermissionsResponse:
    """Replace all project permissions for one project member."""
    result = await project_service.updateUserPermissions(
        project_uuid=project_uuid,
        actor_user_id=user_info["id"],
        target_user_id=user_id,
        permissions=input_data.permissions,
    )
    return result.unwrap()


@project_router.post(
    "/{project_uuid}/archive",
    response_model=ProjectArchiveResponse,
)
async def archive_project(
    user_info: Annotated[
        UserInfo,
        Depends(requiredProjectPermission(ProjectPermission.OWNER)),
    ],
    project_uuid: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectArchiveResponse:
    """Archive a project owned by the current actor."""
    result = await project_service.setProjectArchived(
        project_uuid=project_uuid, archived=True
    )
    return result.unwrap()


@project_router.post(
    "/{project_uuid}/unarchive",
    response_model=ProjectArchiveResponse,
)
async def unarchive_project(
    user_info: Annotated[
        UserInfo,
        Depends(
            requiredProjectPermission(
                ProjectPermission.OWNER, allow_archived=True
            )
        ),
    ],
    project_uuid: Annotated[str, Path()],
    project_service: Annotated[ProjectService, Depends(getProjectService)],
) -> ProjectArchiveResponse:
    """Unarchive a project owned by the current actor."""
    result = await project_service.setProjectArchived(
        project_uuid=project_uuid, archived=False
    )
    return result.unwrap()
