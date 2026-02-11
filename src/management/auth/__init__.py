"""Authentication and authorization module for management API."""

from .roles import ManagementRole, get_effective_roles
from .entities import UserInfo
from .services import (
    AuthService,
    ForbiddenError,
    UnauthorizedError,
    InsufficientPermissionsError,
)
from .factories import getAuthService
from .dependencies import (
    getUserInfo,
    requireRole,
    requireAnyRole,
    requireAllRoles,
)


__all__ = [
    # Entities
    "UserInfo",
    # Roles
    "ManagementRole",
    "get_effective_roles",
    # Errors
    "UnauthorizedError",
    "ForbiddenError",
    "InsufficientPermissionsError",
    # Dependencies
    "getUserInfo",
    "requireRole",
    "requireAnyRole",
    "requireAllRoles",
    # Services
    "AuthService",
    "getAuthService",
]
