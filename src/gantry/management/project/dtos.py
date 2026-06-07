"""DTOs for Project module."""

from gantry.shared.dtos.base import BaseDTO

from pydantic import Field


class ProjectListQuery(BaseDTO):
    """Query for listing projects."""

    organization: str | None = Field(
        None,
        description="Organization id. If provided, returns org-wide projects.",
    )
    q: str | None = Field(None, description="Optional project search text")


class PaginationQuery(BaseDTO):
    """Shared pagination query parameters."""

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    q: str | None = Field(None, description="Optional search text")


class CreateProjectRequest(BaseDTO):
    """Body for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)


class UpdateProjectRequest(BaseDTO):
    """Body for updating project metadata."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)


class ProjectSettingsResponse(BaseDTO):
    """Project settings response."""

    rate_limit: int | None = Field(
        None,
        description=(
            "Requests per minute. null means inherit organization/default."
        ),
    )
    spending_limit: int | None = Field(
        None,
        ge=0,
        description=(
            "Monthly spending limit as a scaled integer. null means unlimited."
        ),
    )
    extra: dict = Field(
        default_factory=dict,
        description="Additional settings as a flat key-value map",
    )


class UpdateProjectSettingsRequest(BaseDTO):
    """Body for updating project settings."""

    rate_limit: int | None = Field(
        None,
        ge=1,
        description="Requests per minute; null to inherit organization limit",
    )
    spending_limit: int | None = Field(
        None,
        ge=0,
        description="Monthly spending limit as a scaled integer; null for unlimited",
    )
    extra: dict = Field(
        default_factory=dict,
        description="Flat key-value pairs for additional settings",
    )


class ProjectInfoResponse(BaseDTO):
    """Project metadata response."""

    project_uuid: str = Field(..., description="Project UUID")
    name: str
    description: str | None = None
    organization_id: str
    archived: bool


class ProjectListResponse(BaseDTO):
    """Paginated project list response."""

    total: int
    results: list[ProjectInfoResponse]


class AddProjectUserRequest(BaseDTO):
    """Body for adding user to project."""

    user_id: str = Field(..., min_length=1, max_length=128)


class ProjectUserResponse(BaseDTO):
    """Project user item."""

    id: str
    username: str | None = None
    email: str | None = None


class ProjectUserListResponse(BaseDTO):
    """Paginated project users."""

    total: int
    results: list[ProjectUserResponse]


class ProjectUserPermissionsRequest(BaseDTO):
    """Body for updating project user permissions."""

    permissions: list[str] = Field(
        ...,
        description="Full replacement list of project permissions",
    )


class ProjectUserPermissionsResponse(BaseDTO):
    """Project user permissions response."""

    permissions: list[str]


class ProjectArchiveResponse(BaseDTO):
    """Archive/unarchive response."""

    id: str
    archived: bool


class ProjectPermissionCatalogResponse(BaseDTO):
    """All supported project permissions without storage prefix."""

    permissions: list[str]
