"""Helpers for reading and writing admin-visible permission summaries."""

from gantry.shared.utils.permission_utils import (
    normalize_project_permission_map,
    serialize_project_permission_map,
)
from gantry.management.project.permissions import (
    get_effective_permissions as get_effective_project_permissions,
)
from gantry.management.organization.permissions import (
    get_effective_permissions as get_effective_org_permissions,
)

from .dtos import (
    AdminUserPermissionSummaryResponse,
    AdminUserProjectPermissionResponse,
    AdminUserProjectPermissionUpdateRequest,
)

from typing import Any


ORG_PERMISSIONS_ATTR = "org_permissions"
PROJECT_PERMISSIONS_ATTR = "project_permissions"


def normalize_string_list(raw: Any) -> list[str]:
    """Normalize a Keycloak multivalued attribute into plain strings."""
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [value for value in raw if isinstance(value, str)]
    return []


def build_project_permission_summary(
    attrs: dict[str, Any],
) -> list[AdminUserProjectPermissionResponse]:
    """Group project permissions by project uuid."""
    grouped = normalize_project_permission_map(
        attrs.get(PROJECT_PERMISSIONS_ATTR)
    )
    return [
        AdminUserProjectPermissionResponse(
            project_uuid=project_uuid,
            permissions=sorted(permissions),
            effective_permissions=sorted(
                get_effective_project_permissions(sorted(permissions))
            ),
        )
        for project_uuid, permissions in sorted(grouped.items())
    ]


def build_permission_summary(
    attrs: dict[str, Any],
) -> AdminUserPermissionSummaryResponse:
    """Map raw Keycloak user attributes into a structured permission view."""
    organization_permissions = normalize_string_list(
        attrs.get(ORG_PERMISSIONS_ATTR)
    )
    return AdminUserPermissionSummaryResponse(
        organization_permissions=organization_permissions,
        effective_organization_permissions=sorted(
            get_effective_org_permissions(organization_permissions)
        ),
        project_permissions=build_project_permission_summary(attrs),
    )


def flatten_project_permission_updates(
    project_permissions: list[AdminUserProjectPermissionUpdateRequest],
) -> dict[str, list[str]]:
    """Encode grouped project permissions into the persisted map format."""
    return serialize_project_permission_map(
        {item.project_uuid: item.permissions for item in project_permissions}
    )
