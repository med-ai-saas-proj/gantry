"""Authentication and authorization module for management API."""

from .entities import UserInfo
from .roles import ManagementRole, get_effective_roles, has_role, has_any_role, has_all_roles
from .authorization import (
    ForbiddenError,
    InsufficientPermissionsError,
    require_role,
    require_any_role,
    require_all_roles,
    check_role,
    check_any_role,
    check_all_roles,
)
from .dependencies import getUserInfo
from .services import KeycloakService

__all__ = [
    # Entities
    "UserInfo",
    # Roles
    "ManagementRole",
    "get_effective_roles",
    "has_role",
    "has_any_role",
    "has_all_roles",
    # Authorization
    "ForbiddenError",
    "InsufficientPermissionsError",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "check_role",
    "check_any_role",
    "check_all_roles",
    # Dependencies
    "getUserInfo",
    # Services
    "KeycloakService",
]
