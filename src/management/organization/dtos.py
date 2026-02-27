"""Data Transfer Objects for the Organization module."""

from src.shared.dtos.base import BaseDTO

from typing import Any

from pydantic import Field, EmailStr


# Query helpers
class PaginatedQuery(BaseDTO):
    """Shared pagination query parameters."""

    limit: int = Field(20, ge=1, le=100, description="Max items to return")
    offset: int = Field(0, ge=0, description="Number of items to skip")
    q: str | None = Field(
        None,
        description="Search query forwarded to Keycloak",
    )


# Organization
class OrgInfoOutput(BaseDTO):
    """Organization metadata."""

    id: str
    name: str
    owner_id: str | None = None


class DeleteRequestOutput(BaseDTO):
    """Org deletion request acknowledgement."""

    org_id: str
    cancel_before: str = Field(
        ...,
        description="ISO-8601 timestamp; request can be cancelled before this",
    )


class CancelDeleteRequestOutput(BaseDTO):
    """Org deletion cancellation acknowledgement."""

    org_id: str
    cancelled: bool


class UpdateOrgMetadataInput(BaseDTO):
    """Body for updating basic org metadata."""

    name: str = Field(..., min_length=1, max_length=256)


# Users
class OrgUserOutput(BaseDTO):
    """A user inside the organization."""

    id: str
    username: str | None = None
    email: str | None = None


class OrgUserListOutput(BaseDTO):
    """Paginated list of org users."""

    total: int
    results: list[OrgUserOutput]


# Projects
class OrgProjectOutput(BaseDTO):
    """A project inside the organization."""

    id: str
    name: str
    description: str | None = None


class OrgProjectListOutput(BaseDTO):
    """Paginated list of org projects."""

    total: int
    results: list[OrgProjectOutput]


class CreateProjectInput(BaseDTO):
    """Body for creating a new project."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field("", max_length=4096)


# Settings
class OrgSettingsOutput(BaseDTO):
    """Organization settings (flattened key-value map)."""

    rate_limit: int | None = Field(
        None,
        description=("Requests per minute. null means inherit global default."),
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings as a flat key-value map",
    )


class UpdateSettingsInput(BaseDTO):
    """Body for PATCH /settings.

    Follows the flattening convention described in the spec, e.g.::

        {
            "user.name": "test",
            "user.age": 33,
        }
    """

    rate_limit: int | None = Field(
        None,
        description="Requests per minute; null to inherit global default",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Flat key-value pairs for additional settings",
    )


# Invitations
class InviteUserInput(BaseDTO):
    """Body for POST /invitations."""

    email: EmailStr
    permissions: list[str] = Field(
        default_factory=list,
        description="Org permissions to assign to the invited user",
    )


class InvitationOutput(BaseDTO):
    """An invitation record."""

    id: str
    email: str
    status: str | None = None
    permissions: list[str] = Field(default_factory=list)


class InvitationListOutput(BaseDTO):
    """List of invitations."""

    results: list[InvitationOutput]


# User permissions
class UserPermissionsOutput(BaseDTO):
    """List of org permissions for a user."""

    permissions: list[str]


class UserPermissionsInput(BaseDTO):
    """Body for PUT /users/{user_id}/permissions."""

    permissions: list[str] = Field(
        ...,
        description="Full replacement list of org permissions",
    )
