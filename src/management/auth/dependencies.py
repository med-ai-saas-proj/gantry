"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer

from .entities import UserInfo
from .factories import AuthService, getAuthService
from .roles import ManagementRole
from .settings import getAuthSettings


auth_settings = getAuthSettings()
server_url_str = auth_settings.server_url.encoded_string()
realm_name = auth_settings.realm_name

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=(
        f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/token"
    ),
    authorizationUrl=(
        f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/auth"
    ),
    refreshUrl=(
        f"{server_url_str}/realms/{realm_name}/protocol/openid-connect/token"
    ),
)


async def getUserInfo(
    token: Annotated[str, Security(oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAuthService)],
) -> UserInfo:
    """
    Get authenticated user info from JWT token.

    This is the base dependency for authentication.
    Returns UserInfo if token is valid, raises UnauthorizedError otherwise.
    """
    return auth_service.verifyToken(token).unwrap()


def requireRole(role: ManagementRole):
    """
    Create a dependency that requires a specific role.

    Usage::

        @router.post(
            "/members"
        )
        async def create_member(
            user_info: Annotated[
                UserInfo,
                Depends(
                    requireRole(
                        ManagementRole.MEMBER_ADD
                    )
                ),
            ],
        ): ...
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkRole(user_info, role).unwrap()
        return user_info

    return dependency


def requireAnyRole(roles: list[ManagementRole]):
    """
    Create a dependency that requires any of the specified roles.

    Usage::

        @router.get(
            "/members"
        )
        async def list_members(
            user_info: Annotated[
                UserInfo,
                Depends(
                    requireAnyRole(
                        [
                            ManagementRole.MEMBER_VIEW,
                            ManagementRole.MEMBER_ADMIN,
                        ]
                    )
                ),
            ],
        ): ...
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkAnyRole(user_info, roles).unwrap()
        return user_info

    return dependency


def requireAllRoles(roles: list[ManagementRole]):
    """
    Create a dependency that requires all of the specified roles.

    Usage::

        @router.post(
            "/admin/critical"
        )
        async def critical_operation(
            user_info: Annotated[
                UserInfo,
                Depends(
                    requireAllRoles(
                        [
                            ManagementRole.SUPER_ADMIN,
                            ManagementRole.AUDIT_VIEW,
                        ]
                    )
                ),
            ],
        ): ...
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkAllRoles(user_info, roles).unwrap()
        return user_info

    return dependency
