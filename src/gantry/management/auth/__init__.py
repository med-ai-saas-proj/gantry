"""Authentication and authorization module for management API."""

from .entities import UserInfo
from .services import (
    AuthService,
    ForbiddenError,
    UnauthorizedError,
    InsufficientPermissionsError,
)
from .settings import getAuthSettings
from .factories import getAuthService, getAdminAuthService
from .dependencies import (
    getUserInfo,
    getAdminInfo,
)


# __all__ = [
#     # Entities
#     "UserInfo",
#     "UnauthorizedError",
#     "ForbiddenError",
#     "InsufficientPermissionsError",
#     # Dependencies
#     "getUserInfo",
#     "getAdminInfo",
#     # Services
#     "AuthService",
#     "getAuthService",
#     "getAdminAuthService",
# ]
