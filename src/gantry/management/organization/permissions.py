"""Organization permission definitions."""

from enum import Enum
from typing import Final


class OrgPermission(str, Enum):
    """Fine-grained organization permissions.

    These permissions are stored per-user within an organization
    and checked via the ``requiredOrgPermission`` dependency.
    """

    # Owner – has every other permission implicitly
    OWNER = "organization.owner"

    # Invitation management
    INVITE = "organization.invite"

    # User management
    USERS_GET_ALL = "organization.users.get_all"
    USERS_REMOVE = "organization.users.remove"

    # User permission management (only owner can grant this)
    USERS_PERMISSIONS_RW = "organization.users.permissions.read_write"

    # Settings management
    SETTINGS_READ = "organization.settings.read"
    SETTINGS_WRITE = "organization.settings.write"

    # Project creation at org scope
    PROJECTS_CREATE = "organization.projects.create"
    PROJECTS_GET_ALL = "organization.projects.get_all"

    BILLING_VIEW_USAGE = "organization.billing.view_usage"
    BILLING_MANAGE = "organization.billing.manage"


# Owner inherits every other permission automatically.
PERMISSION_HIERARCHY: Final[dict[OrgPermission, list[OrgPermission]]] = {
    OrgPermission.OWNER: [
        OrgPermission.INVITE,
        OrgPermission.USERS_GET_ALL,
        OrgPermission.USERS_REMOVE,
        OrgPermission.USERS_PERMISSIONS_RW,
        OrgPermission.SETTINGS_READ,
        OrgPermission.SETTINGS_WRITE,
        OrgPermission.PROJECTS_CREATE,
        OrgPermission.PROJECTS_GET_ALL,
        OrgPermission.BILLING_VIEW_USAGE,
        OrgPermission.BILLING_MANAGE,
    ],
}


ALL_PERMISSIONS: Final[list[str]] = [p.value for p in OrgPermission]


def get_effective_permissions(
    user_permissions: list[str],
) -> set[str]:
    """Expand raw permission list using the hierarchy.

    If a user holds ``organization.owner`` they effectively
    hold every permission listed in ``PERMISSION_HIERARCHY``.
    """
    effective = set(user_permissions)
    for perm_str in user_permissions:
        try:
            perm = OrgPermission(perm_str)
        except ValueError:
            continue
        children = PERMISSION_HIERARCHY.get(perm, [])
        effective.update(c.value for c in children)
    return effective


def has_permission(
    user_permissions: list[str] | None,
    required: OrgPermission,
) -> bool:
    """Check whether the user holds *required* (directly or via hierarchy)."""
    if not user_permissions:
        return False
    return required.value in get_effective_permissions(user_permissions)
