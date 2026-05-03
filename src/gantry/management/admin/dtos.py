"""DTOs for admin management routes."""

from gantry.shared.dtos.base import BaseDTO

from pydantic import Field


class AdminUserInfoResponse(BaseDTO):
    """Authenticated admin user information."""

    id: str
    username: str | None
    email: str | None
    # roles: list[str]


class AdminUserOrganizationInfoResponse(BaseDTO):
    """One organization membership visible to admins."""

    id: str
    name: str | None = None
    alias: str | None = None


class AdminUserProjectPermissionResponse(BaseDTO):
    """Project-scoped permissions grouped by project id."""

    project_id: str
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
