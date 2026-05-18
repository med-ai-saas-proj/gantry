"""Internal typed payloads for organization service logic."""

from typing import Any, TypedDict, NotRequired


class KeycloakOrgPayload(TypedDict, total=False):
    """Subset of Keycloak organization fields used by management services."""

    id: str
    name: str
    alias: str


class KeycloakUserPayload(TypedDict, total=False):
    """Subset of Keycloak user fields used by management services."""

    id: str
    username: str | None
    email: str | None
    attributes: dict[str, Any]


class KeycloakInvitationPayload(TypedDict, total=False):
    """Subset of Keycloak invitation fields mapped to API DTOs."""

    id: str
    email: str
    status: str | None


class UserAttributePayload(TypedDict, total=False):
    """Normalized user attributes returned by KeycloakServiceClient."""

    org_permissions: list[str]
    project_permissions: dict[str, list[str]]


class CreateOrgPayload(TypedDict):
    """Payload for Keycloak organization creation."""

    name: str
    alias: NotRequired[str]
