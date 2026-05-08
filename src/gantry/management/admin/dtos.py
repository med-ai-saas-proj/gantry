"""DTOs for admin management routes."""

from gantry.shared.dtos.base import BaseDTO

from pydantic import Field


class AdminPaginationQuery(BaseDTO):
    """Shared pagination query for admin dashboard lists."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    q: str | None = Field(None, description="Optional search text")


class AdminDashboardSummaryResponse(BaseDTO):
    """Top-level counters for the admin dashboard home screen."""

    organizations: int
    projects: int
    api_keys: int
    users: int


class AdminUserInfoResponse(BaseDTO):
    """Authenticated admin user information."""

    id: str
    username: str | None
    email: str | None


class AdminUserOrganizationInfoResponse(BaseDTO):
    """One organization membership visible to admins."""

    id: str
    name: str | None = None
    alias: str | None = None


class AdminUserListItemResponse(BaseDTO):
    """One Keycloak user in admin dashboard lists."""

    id: str
    username: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool
    email_verified: bool


class AdminUserListResponse(BaseDTO):
    """Paginated Keycloak user list for admin dashboard."""

    total: int
    results: list[AdminUserListItemResponse]


class AdminUserProjectPermissionResponse(BaseDTO):
    """Project-scoped permissions grouped by project id."""

    id: str
    permissions: list[str]
    effective_permissions: list[str]


class AdminUserProjectPermissionUpdateRequest(BaseDTO):
    """Requested project permission slice for one project."""

    project_id: str
    permissions: list[str]


class AdminUserPermissionSummaryResponse(BaseDTO):
    """Normalized permission summary for one user."""

    organization_permissions: list[str]
    effective_organization_permissions: list[str]
    project_permissions: list[AdminUserProjectPermissionResponse]


class AdminUserProfileResponse(BaseDTO):
    """Admin-visible Keycloak user profile and permission summary."""

    id: str
    username: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool
    email_verified: bool
    organizations: list[AdminUserOrganizationInfoResponse]
    permissions: AdminUserPermissionSummaryResponse


class AdminUserPermissionUpdateRequest(BaseDTO):
    """Admin request to replace one user's org/project permission attributes."""

    organization_permissions: list[str] = Field(default_factory=list)
    project_permissions: list[AdminUserProjectPermissionUpdateRequest] = Field(
        default_factory=list
    )
