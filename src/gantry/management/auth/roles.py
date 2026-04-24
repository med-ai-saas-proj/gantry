"""Role-based access control (RBAC) definitions for management API."""

from enum import Enum
from typing import Final


class ManagementRole(str, Enum):
    """Management roles for fine-grained access control.

    These roles are checked from Keycloak JWT token claims.
    Roles should be assigned in Keycloak under the client roles
    for the management application.
    """

    # Super admin - full access to everything
    SUPER_ADMIN = "super_admin"

    # Organization management
    ORG_ADMIN = "org.admin"
    ORG_MEMBER = "org.member"
    ORG_VIEWER = "org.viewer"

    # Member management
    MEMBER_ADMIN = "member.admin"
    MEMBER_ADD = "member.add"
    MEMBER_EDIT = "member.edit"
    MEMBER_DELETE = "member.delete"
    MEMBER_VIEW = "member.view"

    # Permission management
    PERMISSION_ADMIN = "permission.admin"
    PERMISSION_CREATE = "permission.create"
    PERMISSION_EDIT = "permission.edit"
    PERMISSION_DELETE = "permission.delete"
    PERMISSION_VIEW = "permission.view"

    # API Key management
    APIKEY_ADMIN = "apikey.admin"
    APIKEY_CREATE = "apikey.create"
    APIKEY_EDIT = "apikey.edit"
    APIKEY_DELETE = "apikey.delete"
    APIKEY_VIEW = "apikey.view"

    # User management
    USER_ADMIN = "user.admin"
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    USER_VIEW = "user.view"

    # Audit and monitoring
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"

    # Settings management
    SETTINGS_ADMIN = "settings.admin"
    SETTINGS_EDIT = "settings.edit"
    SETTINGS_VIEW = "settings.view"

    # Billing management
    BILLING_VIEW_USAGE = "billing.view_usage"
    BILLING_MANAGE = "billing.manage"
    BILLING_VIEW_CREDITS = "billing.view_credits"


# Role hierarchies - higher roles include permissions of lower roles
ROLE_HIERARCHY: Final[dict[ManagementRole, list[ManagementRole]]] = {
    # Super admin has all permissions
    ManagementRole.SUPER_ADMIN: [
        ManagementRole.ORG_ADMIN,
        ManagementRole.MEMBER_ADMIN,
        ManagementRole.PERMISSION_ADMIN,
        ManagementRole.APIKEY_ADMIN,
        ManagementRole.USER_ADMIN,
        ManagementRole.AUDIT_EXPORT,
        ManagementRole.SETTINGS_ADMIN,
    ],
    # Organization admin
    ManagementRole.ORG_ADMIN: [
        ManagementRole.ORG_MEMBER,
        ManagementRole.ORG_VIEWER,
    ],
    # Member admin includes all member operations
    ManagementRole.MEMBER_ADMIN: [
        ManagementRole.MEMBER_ADD,
        ManagementRole.MEMBER_EDIT,
        ManagementRole.MEMBER_DELETE,
        ManagementRole.MEMBER_VIEW,
    ],
    # Permission admin includes all permission operations
    ManagementRole.PERMISSION_ADMIN: [
        ManagementRole.PERMISSION_CREATE,
        ManagementRole.PERMISSION_EDIT,
        ManagementRole.PERMISSION_DELETE,
        ManagementRole.PERMISSION_VIEW,
    ],
    # API Key admin includes all API key operations
    ManagementRole.APIKEY_ADMIN: [
        ManagementRole.APIKEY_CREATE,
        ManagementRole.APIKEY_EDIT,
        ManagementRole.APIKEY_DELETE,
        ManagementRole.APIKEY_VIEW,
    ],
    # User admin includes all user operations
    ManagementRole.USER_ADMIN: [
        ManagementRole.USER_CREATE,
        ManagementRole.USER_EDIT,
        ManagementRole.USER_DELETE,
        ManagementRole.USER_VIEW,
    ],
    # Settings admin includes settings operations
    ManagementRole.SETTINGS_ADMIN: [
        ManagementRole.SETTINGS_EDIT,
        ManagementRole.SETTINGS_VIEW,
    ],
    # Audit export includes audit view
    ManagementRole.AUDIT_EXPORT: [
        ManagementRole.AUDIT_VIEW,
    ],
}


def get_effective_roles(user_roles: list[str]) -> set[str]:
    """Get all effective roles including inherited roles from hierarchy.

    Args:
        user_roles: List of roles assigned to the user

    Returns:
        Set of all effective roles (assigned + inherited)

    Example:
        >>> get_effective_roles(
        ...     ["member.admin"]
        ... )
        {"member.admin", "member.add", "member.edit", "member.delete", "member.view"}
    """
    effective_roles = set(user_roles)

    # Add inherited roles based on hierarchy
    for role in user_roles:
        try:
            role_enum = ManagementRole(role)
            if role_enum in ROLE_HIERARCHY:
                # Add all child roles
                child_roles = ROLE_HIERARCHY[role_enum]
                effective_roles.update(r.value for r in child_roles)

                # Recursively add grandchild roles
                for child_role in child_roles:
                    if child_role in ROLE_HIERARCHY:
                        grandchild_roles = ROLE_HIERARCHY[child_role]
                        effective_roles.update(
                            r.value for r in grandchild_roles
                        )
        except ValueError:
            # Role not in ManagementRole enum, skip
            continue

    return effective_roles


def has_role(
    user_roles: list[str] | None, required_role: ManagementRole
) -> bool:
    """Check if user has a specific role (including inherited roles).

    Args:
        user_roles: List of roles from user's token
        required_role: The role to check for

    Returns:
        True if user has the role (directly or inherited)

    Example:
        >>> has_role(
        ...     [
        ...         "member.admin"
        ...     ],
        ...     ManagementRole.MEMBER_ADD,
        ... )
        True
        >>> has_role(
        ...     ["member.view"],
        ...     ManagementRole.MEMBER_ADD,
        ... )
        False
    """
    if not user_roles:
        return False

    effective_roles = get_effective_roles(user_roles)
    return required_role.value in effective_roles


def has_any_role(
    user_roles: list[str] | None, required_roles: list[ManagementRole]
) -> bool:
    """Check if user has any of the specified roles.

    Args:
        user_roles: List of roles from user's token
        required_roles: List of roles to check for (user needs at least one)

    Returns:
        True if user has at least one of the required roles
    """
    if not user_roles:
        return False

    effective_roles = get_effective_roles(user_roles)
    return any(role.value in effective_roles for role in required_roles)


def has_all_roles(
    user_roles: list[str] | None, required_roles: list[ManagementRole]
) -> bool:
    """Check if user has all of the specified roles.

    Args:
        user_roles: List of roles from user's token
        required_roles: List of roles to check for (user needs all)

    Returns:
        True if user has all of the required roles
    """
    if not user_roles:
        return False

    effective_roles = get_effective_roles(user_roles)
    return all(role.value in effective_roles for role in required_roles)
