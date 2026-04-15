"""Data Transfer Objects for the Organization module."""

from gantry.shared.dtos.base import BaseDTO

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
class OrgInfoResponse(BaseDTO):
    """Organization metadata."""

    id: str
    name: str
    owner_id: str | None = None


class DeleteRequestResponse(BaseDTO):
    """Org deletion request acknowledgement."""

    org_id: str
    requested_at: str = Field(
        ...,
        description="ISO-8601 timestamp when deletion was requested",
    )
    cancel_before: str = Field(
        ...,
        description=(
            "ISO-8601 timestamp deadline to cancel deletion "
            "before hard-delete is executed"
        ),
    )


class DeleteCancelResponse(BaseDTO):
    """Deletion cancel acknowledgement."""

    org_id: str
    cancelled: bool = Field(
        True,
        description="Always true when cancellation succeeds",
    )


class UpdateOrgMetadataRequest(BaseDTO):
    """Body for updating basic org metadata."""

    name: str = Field(..., min_length=1, max_length=256)


# Users
class OrgUserResponse(BaseDTO):
    """A user inside the organization."""

    id: str
    username: str | None = None
    email: str | None = None


class OrgUserListResponse(BaseDTO):
    """Paginated list of org users."""

    total: int
    results: list[OrgUserResponse]


# Settings
class OrgSettingsResponse(BaseDTO):
    """Organization settings (flattened key-value map)."""

    rate_limit: int | None = Field(
        None,
        description=("Requests per minute. null means inherit global default."),
    )
    spending_limit: int | None = Field(
        None,
        ge=0,
        description=(
            "Monthly spending limit as a scaled integer. null means unlimited."
        ),
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional settings as a flat key-value map",
    )


class UpdateSettingsRequest(BaseDTO):
    """Body for PATCH /settings.

    Follows the flattening convention described in the spec, e.g.::

        {
            "user.name": "test",
            "user.age": 33,
        }
    """

    rate_limit: int | None = Field(
        None,
        ge=1,
        description="Requests per minute; null to inherit global default",
    )
    spending_limit: int | None = Field(
        None,
        ge=0,
        description="Monthly spending limit as a scaled integer; null for unlimited",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Flat key-value pairs for additional settings",
    )


# Invitations
class InviteUserRequest(BaseDTO):
    """Body for POST /invitations."""

    email: EmailStr


class InvitationResponse(BaseDTO):
    """An invitation record."""

    id: str
    email: str
    status: str | None = None


class InvitationListResponse(BaseDTO):
    """List of invitations."""

    results: list[InvitationResponse]


# User permissions
class UserPermissionsResponse(BaseDTO):
    """List of org permissions for a user."""

    permissions: list[str]


class UserPermissionsRequest(BaseDTO):
    """Body for PUT /users/{user_id}/permissions."""

    permissions: list[str] = Field(
        ...,
        description="Full replacement list of org permissions",
    )


class PermissionCatalogResponse(BaseDTO):
    """All supported permissions for one permission scope."""

    permissions: list[str]
