"""Authentication and authorization module for management API."""

from .entities import UserInfo
from .roles import ManagementRole, get_effective_roles
from .services import (
    AuthService,
    UnauthorizedError,
    ForbiddenError,
    InsufficientPermissionsError,
)
from .dependencies import (
    getUserInfo,
    requireRole,
    requireAnyRole,
    requireAllRoles,
)
from .factories import getAuthService

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
