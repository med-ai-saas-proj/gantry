"""Admin-only management routes."""

from gantry.settings import ApiGatewayRoute
from gantry.settings import getAppSettings
from gantry.management.auth import AdminInfo, getAdminInfo
from gantry.management.api_key.dtos import (
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyWriteRequest,
    ApiKeyUpdateRequest,
    ApiKeyCreateResponse,
    ApiKeyPermissionCatalogResponse,
)
from gantry.management.project.dtos import (
    ProjectInfoResponse,
    ProjectListResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectArchiveResponse,
    ProjectSettingsResponse,
    ProjectUserListResponse,
    UpdateProjectSettingsRequest,
    ProjectUserPermissionsRequest,
    ProjectPermissionCatalogResponse,
)
from gantry.management.organization.dtos import (
    OrgInfoResponse,
    OrgListResponse,
    CreateOrgRequest,
    OrgSettingsResponse,
    OrgUserListResponse,
    DeleteCancelResponse,
    DeleteRequestResponse,
    UpdateSettingsRequest,
    UserPermissionsRequest,
    UpdateOrgMetadataRequest,
    PermissionCatalogResponse,
)

from .dtos import (
    AdminPaginationQuery,
    AdminUserInfoResponse,
    AdminUserListResponse,
    AdminUserProfileResponse,
    AdminDashboardSummaryResponse,
    AdminAddOrganizationUserRequest,
    AdminUserPermissionUpdateRequest,
    AdminUserOrganizationInfoResponse,
    AdminUserPermissionSummaryResponse,
)
from .factories import AdminService, getAdminService

from typing import Annotated

from fastapi import Body, Path, Query, Depends, Response, APIRouter


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get(
    "/me",
    response_model=AdminUserInfoResponse,
    summary="Get authenticated admin user info",
)
async def get_admin_me(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserInfoResponse:
    """Return the current admin user after ADMIN realm-role verification."""
    return admin_service.getAdminInfo(admin_info)


@admin_router.get(
    "/dashboard/summary",
    response_model=AdminDashboardSummaryResponse,
    summary="Get top-level admin dashboard counters",
)
async def get_admin_dashboard_summary(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminDashboardSummaryResponse:
    """Return summary counters so the dashboard need not fan out to list APIs."""
    del admin_info
    return await admin_service.getDashboardSummary()


@admin_router.get(
    "/organizations/permissions",
    response_model=PermissionCatalogResponse,
    summary="List organization permissions for admin UIs",
)
async def list_admin_organization_permissions(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> PermissionCatalogResponse:
    """Return the organization permission catalog."""
    del admin_info
    return admin_service.listOrganizationPermissions()


@admin_router.get(
    "/organizations",
    response_model=OrgListResponse,
    summary="List organizations for admin dashboard",
)
async def list_admin_organizations(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgListResponse:
    """Return organizations without requiring membership in each org."""
    del admin_info
    return await admin_service.listOrganizations(pagination)


@admin_router.post(
    "/organizations",
    response_model=OrgInfoResponse,
    status_code=201,
    summary="Create an organization as admin",
)
async def create_admin_organization(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    input_data: Annotated[CreateOrgRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgInfoResponse:
    """Create an organization and optionally seed an owner membership."""
    del admin_info
    return await admin_service.createOrganization(input_data)


@admin_router.get(
    "/organizations/{org_id}",
    response_model=OrgInfoResponse,
    summary="Get organization details as admin",
)
async def get_admin_organization(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgInfoResponse:
    """Return one organization without user-scope permission checks."""
    del user_info
    return await admin_service.getOrganization(org_id)


@admin_router.get(
    "/organizations/{org_id}/settings",
    response_model=OrgSettingsResponse,
    summary="Get organization settings as admin",
)
async def get_admin_organization_settings(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgSettingsResponse:
    """Return organization settings without requiring org membership."""
    del user_info
    return await admin_service.getOrganizationSettings(org_id)


@admin_router.patch(
    "/organizations/{org_id}/settings",
    response_model=OrgSettingsResponse,
    summary="Update organization settings as admin",
)
async def update_admin_organization_settings(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    input_data: Annotated[UpdateSettingsRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgSettingsResponse:
    """Update organization settings without requiring org-owner permission."""
    del user_info
    return await admin_service.updateOrganizationSettings(org_id, input_data)


@admin_router.get(
    "/organizations/{org_id}/users",
    response_model=OrgUserListResponse,
    summary="List organization users as admin",
)
async def list_admin_organization_users(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgUserListResponse:
    """Canonical admin path for organization-user listings."""
    del user_info
    return await admin_service.listOrganizationUsers(org_id, pagination)


@admin_router.post(
    "/organizations/{org_id}/users",
    response_model=AdminUserProfileResponse,
    status_code=201,
    summary="Add organization user as admin",
)
async def add_admin_organization_user(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    payload: Annotated[AdminAddOrganizationUserRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Add a user to an organization and optionally seed permissions."""
    del user_info
    return await admin_service.addOrganizationUser(
        org_id,
        payload.user_id,
        payload.permissions,
    )


@admin_router.put(
    "/organizations/{org_id}/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Replace user organization permissions as admin",
)
async def set_admin_organization_user_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    payload: Annotated[UserPermissionsRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Replace only organization permissions and preserve project permissions."""
    del user_info
    return await admin_service.setUserOrganizationPermissions(
        user_id,
        org_id,
        payload.permissions,
    )


@admin_router.patch(
    "/organizations/{org_id}",
    response_model=OrgInfoResponse,
    summary="Update organization details as admin",
)
async def update_admin_organization(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    input_data: Annotated[UpdateOrgMetadataRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> OrgInfoResponse:
    """Rename one organization without requiring org owner permission."""
    del user_info
    return await admin_service.updateOrganization(org_id, input_data)


@admin_router.delete(
    "/organizations/{org_id}",
    status_code=202,
    response_model=DeleteRequestResponse,
    summary="Request organization deletion as admin",
)
async def delete_admin_organization(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> DeleteRequestResponse:
    """Request delayed organization deletion through the existing lifecycle."""
    del user_info
    return await admin_service.deleteOrganization(org_id)


@admin_router.post(
    "/organizations/{org_id}/deletion/cancel",
    response_model=DeleteCancelResponse,
    summary="Cancel organization deletion as admin",
)
async def cancel_delete_admin_organization(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> DeleteCancelResponse:
    """Cancel a delayed organization deletion without org-owner permission."""
    del user_info
    return await admin_service.cancelDeleteOrganization(org_id)


@admin_router.get(
    "/projects/permissions",
    response_model=ProjectPermissionCatalogResponse,
    summary="List project permissions for admin UIs",
)
async def list_admin_project_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectPermissionCatalogResponse:
    """Return the project permission catalog."""
    del user_info
    return admin_service.listProjectPermissions()


@admin_router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List projects in an organization as admin",
)
async def list_admin_projects(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Query(..., min_length=1, alias="org_id")],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectListResponse:
    """Return projects for one organization without project membership checks."""
    del user_info
    return await admin_service.listProjects(org_id, pagination)


@admin_router.post(
    "/projects",
    response_model=ProjectInfoResponse,
    status_code=201,
    summary="Create project as admin",
)
async def create_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: Annotated[str, Query(..., min_length=1, alias="org_id")],
    input_data: Annotated[CreateProjectRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectInfoResponse:
    """Create a project in one organization without user-scoped checks."""
    del user_info
    return await admin_service.createProject(org_id, input_data)


@admin_router.get(
    "/projects/{project_id}",
    response_model=ProjectInfoResponse,
    summary="Get project details as admin",
)
async def get_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectInfoResponse:
    """Return one project without requiring project membership."""
    del user_info
    return await admin_service.getProject(project_id)


@admin_router.get(
    "/projects/{project_id}/settings",
    response_model=ProjectSettingsResponse,
    summary="Get project settings as admin",
)
async def get_admin_project_settings(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectSettingsResponse:
    """Return project settings without requiring project membership."""
    del user_info
    return await admin_service.getProjectSettings(project_id)


@admin_router.patch(
    "/projects/{project_id}/settings",
    response_model=ProjectSettingsResponse,
    summary="Update project settings as admin",
)
async def update_admin_project_settings(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    input_data: Annotated[UpdateProjectSettingsRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectSettingsResponse:
    """Update project settings without requiring project permission checks."""
    del user_info
    return await admin_service.updateProjectSettings(project_id, input_data)


@admin_router.get(
    "/projects/{project_id}/users",
    response_model=ProjectUserListResponse,
    summary="List project users as admin",
)
async def list_admin_project_users(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectUserListResponse:
    """Canonical admin path for project-user listings."""
    del user_info
    return await admin_service.listProjectUsers(project_id, pagination)


@admin_router.put(
    "/projects/{project_id}/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Replace user project permissions as admin",
)
async def set_admin_project_user_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    payload: Annotated[ProjectUserPermissionsRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Replace permissions for one project and preserve other permissions."""
    del user_info
    return await admin_service.setUserProjectPermissions(
        user_id,
        project_id,
        payload.permissions,
    )


@admin_router.put(
    "/projects/{project_id}",
    response_model=ProjectInfoResponse,
    summary="Update project details as admin",
)
async def update_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    input_data: Annotated[UpdateProjectRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectInfoResponse:
    """Update one project without project permission checks."""
    del user_info
    return await admin_service.updateProject(project_id, input_data)


@admin_router.delete(
    "/projects/{project_id}",
    response_model=ProjectArchiveResponse,
    summary="Archive project as admin",
)
async def delete_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectArchiveResponse:
    """Soft-delete one project by marking it archived."""
    del user_info
    return await admin_service.deleteProject(project_id)


@admin_router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectArchiveResponse,
    summary="Archive project as admin",
)
async def archive_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectArchiveResponse:
    """Archive one project without project permission checks."""
    del user_info
    return await admin_service.archiveProject(project_id)


@admin_router.post(
    "/projects/{project_id}/unarchive",
    response_model=ProjectArchiveResponse,
    summary="Unarchive project as admin",
)
async def unarchive_admin_project(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ProjectArchiveResponse:
    """Unarchive one project without project permission checks."""
    del user_info
    return await admin_service.unarchiveProject(project_id)


@admin_router.get(
    "/api-keys/permissions",
    response_model=ApiKeyPermissionCatalogResponse,
    summary="List API-key permissions for admin UIs",
)
async def list_admin_api_key_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ApiKeyPermissionCatalogResponse:
    """Return the API-key permission catalog."""
    del user_info
    return admin_service.listApiKeyPermissions()


@admin_router.get(
    "/api-keys",
    response_model=ApiKeyListResponse,
    summary="List project API keys as admin",
)
async def list_admin_api_keys(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Query(..., min_length=1, alias="project_id")],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
    disabled: Annotated[bool | None, Query()] = None,
) -> ApiKeyListResponse:
    """Return API keys for one project without project permission checks."""
    del user_info
    return await admin_service.listApiKeys(project_id, disabled=disabled)


@admin_router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=201,
    summary="Create project API key as admin",
)
async def create_admin_api_key(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    project_id: Annotated[str, Query(..., min_length=1, alias="project_id")],
    input_data: Annotated[ApiKeyWriteRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ApiKeyCreateResponse:
    """Create an API key in one project without project permission checks."""
    return await admin_service.createApiKey(user_info, project_id, input_data)


@admin_router.get(
    "/api-keys/{api_key_uuid}",
    response_model=ApiKeyResponse,
    summary="Get API key as admin",
)
async def get_admin_api_key(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
    disabled: Annotated[bool | None, Query()] = None,
) -> ApiKeyResponse:
    """Return one API key without project permission checks."""
    del user_info
    return await admin_service.getApiKey(api_key_uuid, disabled=disabled)


@admin_router.put(
    "/api-keys/{api_key_uuid}",
    response_model=ApiKeyResponse,
    summary="Update API key as admin",
)
async def update_admin_api_key(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    input_data: Annotated[ApiKeyUpdateRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> ApiKeyResponse:
    """Update one API key without project permission checks."""
    del user_info
    return await admin_service.updateApiKey(api_key_uuid, input_data)


@admin_router.delete(
    "/api-keys/{api_key_uuid}",
    summary="Delete API key as admin",
)
async def delete_admin_api_key(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    api_key_uuid: Annotated[str, Path(min_length=1)],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> Response:
    """Delete one API key without project permission checks."""
    del user_info
    await admin_service.deleteApiKey(api_key_uuid)
    return Response(status_code=200)


@admin_router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List users for admin dashboard",
)
async def list_admin_users(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserListResponse:
    """List Keycloak users with pagination and optional search."""
    del user_info
    return await admin_service.listUsers(pagination)


@admin_router.get(
    "/users/unassigned",
    response_model=AdminUserListResponse,
    summary="List users without organization membership",
)
async def list_admin_unassigned_users(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    pagination: Annotated[AdminPaginationQuery, Depends()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserListResponse:
    """List Keycloak users that can be selected as a new organization owner."""
    del user_info
    return await admin_service.listUnassignedUsers(pagination)


@admin_router.get(
    "/users/{user_id}/organizations",
    response_model=list[AdminUserOrganizationInfoResponse],
    summary="List organizations for a specific user",
)
async def get_user_organizations(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    user_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> list[AdminUserOrganizationInfoResponse]:
    """Canonical admin path for user-organization lookups."""
    del user_info
    return await admin_service.getUserOrganizations(user_id)


@admin_router.get(
    "/users/{user_id}/profile",
    response_model=AdminUserProfileResponse,
    summary="Get Keycloak profile and permissions for a specific user",
)
async def get_user_profile(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    user_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Return one user's Keycloak profile plus normalized permission data."""
    del user_info
    return await admin_service.getUserProfile(user_id)


@admin_router.get(
    "/users/{user_id}/permissions",
    response_model=AdminUserPermissionSummaryResponse,
    summary="Get Keycloak org/project permissions for a specific user",
)
async def get_user_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    user_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserPermissionSummaryResponse:
    """Return one user's normalized org/project permission summary."""
    del user_info
    return await admin_service.getUserPermissions(user_id)


@admin_router.put(
    "/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Replace Keycloak org/project permissions for a specific user",
)
async def set_user_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    user_id: Annotated[str, Path()],
    payload: Annotated[AdminUserPermissionUpdateRequest, Body()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Replace one user's permission attributes through Keycloak admin API."""
    del user_info
    return await admin_service.setUserPermissions(user_id, payload)


@admin_router.delete(
    "/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Reset Keycloak org/project permissions for a specific user",
)
async def reset_user_permissions(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    user_id: Annotated[str, Path()],
    admin_service: Annotated[AdminService, Depends(getAdminService)],
) -> AdminUserProfileResponse:
    """Clear one user's org/project permission attributes in Keycloak."""
    del user_info
    return await admin_service.resetUserPermissions(user_id)

@admin_router.get(
    "/registered-routes",
    summary="Get registered routes",
    response_model=dict[str, ApiGatewayRoute]
)
async def getRegisteredRoutes(
    user_info: Annotated[AdminInfo, Depends(getAdminInfo)],
):
    routes = getAppSettings().api_gateway.routes
    return routes
