"""FastAPI dependencies for authentication and authorization."""

from gantry.keycloak import getKeycloakSettings
from gantry.settings import AppStage, getAppSettings
from gantry.shared.custom_types.error_exception import RecoverableError

from .entities import UserInfo, AdminInfo
from .factories import (
    AuthService,
    getAuthService,
    getAdminAuthService,
)

import os
from re import A
from math import e
from uuid import UUID
from typing import Annotated

from fastapi import Depends, Security, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer


keycloak_settings = getKeycloakSettings()
server_url_str = keycloak_settings.server_url.encoded_string()
realm_name = keycloak_settings.realm_name

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

admin_oauth_2_scheme = OAuth2AuthorizationCodeBearer(
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


class MissingOrganizationContextError(RecoverableError):
    """Raised when the authenticated token has no organization context."""

    status = 403
    code = "missing_org_context"
    title = "Missing Organization Context"
    detail = "The authenticated token does not include an organization id."


app_settings = getAppSettings()
enable_mock_auth = os.getenv("GANTRY_ENABLE_MOCK_AUTH", "").lower() in {
    "1",
    "true",
    "yes",
}


async def _getUserInfo(
    token: Annotated[str, Security(oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAuthService)],
) -> UserInfo:
    """Get authenticated user info from JWT token.

    This is the base dependency for authentication.
    Returns UserInfo if token is valid, raises UnauthorizedError otherwise.
    """
    user_info = (await auth_service.verifyToken(token)).unwrap()
    return user_info


getUserInfo = _getUserInfo


async def _getAdminInfo(
    token: Annotated[str, Security(admin_oauth_2_scheme)],
    admin_auth_service: Annotated[AuthService, Depends(getAdminAuthService)],
) -> AdminInfo:
    """Get authenticated admin user info and require Keycloak realm role `ADMIN`."""
    user_info = admin_auth_service.verifyTokenAdmin(token).unwrap()
    return user_info


getAdminInfo = _getAdminInfo

if app_settings.stage == AppStage.DEV and enable_mock_auth:
    from gantry.management.auth.services import UnauthorizedError

    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    # If mock_auth is enabled, bypass all auth checks and return a dummy UserInfo
    security = HTTPBearer()

    async def mock_getUserInfo(
        auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        if auth.credentials == "bypass_token":
            return UserInfo(
                id="test_user",
                username="test_user",
                email="test_user@example.com",
                roles=[],
                org_id="test_org1",
                project_uids=[],
            )
        raise UnauthorizedError()

    getUserInfo = mock_getUserInfo

    async def mock_getAdminUserInfo(
        auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> AdminInfo:
        if auth.credentials == "bypass_token":
            return AdminInfo(
                id="test_admin",
                username="test_admin",
                email="test_admin@example.com",
            )
        raise UnauthorizedError()

    getAdminInfo = mock_getAdminUserInfo


async def getUserOrgUuid(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
) -> str:
    """Return the authenticated user's organization id from token context."""
    return user_info["org_uuid"]


async def requireUserOrgUuid(
    org_id: Annotated[str, Depends(getUserOrgUuid)],
) -> str:
    """Return token org id, failing if the token has no organization context."""
    if not org_id:
        raise MissingOrganizationContextError()
    return org_id


def check_access_to_project(user_info: UserInfo, project_uid: UUID):
    if (
        "organization.owner" not in user_info["roles"]
        and str(project_uid) not in user_info["project_uids"]
    ):
        raise HTTPException(
            status_code=403, detail="User does not have access to this project"
        )


def check_access_to_projects(user_info: UserInfo, project_uids: set[str]):
    if "organization.owner" not in user_info[
        "roles"
    ] and not project_uids.issubset(set(user_info["project_uids"])):
        raise HTTPException(
            status_code=403,
            detail=f"You don't have access to some of the specified projects {project_uids - set(user_info['project_uids'])}",
        )


def requireRole(role: ManagementRole):
    """Create a dependency that requires a specific role.

    Usage:
    ```python
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
    ```
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkRole(user_info, role).unwrap()
        return user_info

    if enable_mock_auth and app_settings.stage == AppStage.DEV:
        from gantry.management.auth.services import UnauthorizedError

        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

        # If mock_auth is enabled, bypass all auth checks and return a dummy UserInfo
        security = HTTPBearer()

        async def mock_dependency(
            auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        ) -> UserInfo:
            if auth.credentials == "bypass_token":
                return UserInfo(
                    id="test_user",
                    username="test_user",
                    email="test_user@example.com",
                    roles=[],
                    org_id="test_org1",
                    project_uids=[str(UUID(int=0))],
                )
            raise UnauthorizedError()

        return mock_dependency

    return dependency


def requireAnyRole(roles: list[ManagementRole]):
    """Create a dependency that requires any of the specified roles.

    Usage:
    ```python
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
    ```
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkAnyRole(user_info, roles).unwrap()
        return user_info

    if enable_mock_auth and app_settings.stage == AppStage.DEV:
        from gantry.management.auth.services import UnauthorizedError

        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

        # If mock_auth is enabled, bypass all auth checks and return a dummy UserInfo
        security = HTTPBearer()

        async def mock_dependency(
            auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        ) -> UserInfo:
            if auth.credentials == "bypass_token":
                return UserInfo(
                    id="test_user",
                    username="test_user",
                    email="test_user@example.com",
                    roles=[],
                    org_id="test_org1",
                    project_uids=[str(UUID(int=0))],
                )
            raise UnauthorizedError()

        return mock_dependency

    return dependency


def requireAllRoles(roles: list[ManagementRole]):
    """Create a dependency that requires all of the specified roles.

    Usage:
    ```python
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
    ```
    """

    async def dependency(
        token: Annotated[str, Security(oauth_2_scheme)],
        auth_service: Annotated[AuthService, Depends(getAuthService)],
    ) -> UserInfo:
        user_info = auth_service.verifyToken(token).unwrap()
        auth_service.checkAllRoles(user_info, roles).unwrap()
        return user_info

    return dependency
