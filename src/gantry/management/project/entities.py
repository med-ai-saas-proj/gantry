"""Internal typed payloads for project service logic."""

from typing import TypedDict


class UserAttributePayload(TypedDict, total=False):
    """Normalized user attributes returned by KeycloakServiceClient."""

    org_permissions: list[str]
    project_permissions: dict[str, list[str]]


class KeycloakOrgPayload(TypedDict, total=False):
    """Subset of Keycloak organization membership fields used by projects."""

    id: str


class KeycloakUserPayload(TypedDict, total=False):
    """Subset of Keycloak user fields used by project member listing."""

    id: str
    username: str | None
    email: str | None
