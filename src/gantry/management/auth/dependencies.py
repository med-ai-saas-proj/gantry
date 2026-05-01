"""FastAPI dependencies for authentication and authorization."""

from gantry.keycloak import getKeycloakSettings
from gantry.settings import AppStage, getAppSettings
from gantry.management.organization.factories import (
    KeycloakServiceClient,
    getKeycloakServiceClient,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .roles import ManagementRole
from .entities import UserInfo, AdminInfo
from .settings import getAuthSettings
from .factories import (
    AuthService,
    getAuthService,
    getAdminAuthService,
)

import os
from typing import Annotated

from fastapi import Depends, Security
from pyrusult import ResultStatus
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
    kc_org_client: Annotated[
        KeycloakServiceClient, Depends(getKeycloakServiceClient)
    ],
) -> UserInfo:
    """Get authenticated user info from JWT token.

    This is the base dependency for authentication.
    Returns UserInfo if token is valid, raises UnauthorizedError otherwise.
    """
    user_info = auth_service.verifyToken(token).unwrap()

    org_claim = user_info["org_id"]
    if not org_claim:
        return user_info

    orgs_res = await kc_org_client.getMemberOrganizations(user_info["id"])
    if orgs_res.status == ResultStatus.Err:
        return user_info

    for org in orgs_res.unwrap():
        org_id = org.get("id")
        if not isinstance(org_id, str) or not org_id:
            continue
        if org_claim in {org_id, org.get("name"), org.get("alias")}:
            user_info["org_id"] = org_id
            break

    return user_info


getUserInfo = _getUserInfo


async def _getAdminInfo(
    token: Annotated[str, Security(admin_oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAdminAuthService)],
) -> AdminInfo:
    """Get authenticated admin user info and require Keycloak realm role `ADMIN`."""
    user_info = auth_service.verifyToken(token).unwrap()
    auth_service.checkAdminRole(user_info).unwrap()
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
                project_ids=[],
            )
        raise UnauthorizedError()

    getUserInfo = mock_getUserInfo

    async def mock_getAdminUserInfo(
        auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> UserInfo:
        if auth.credentials == "bypass_token":
            return UserInfo(
                id="test_admin",
                username="test_admin",
                email="test_admin@example.com",
                roles=[AuthService.ADMIN_REALM_ROLE],
                org_id="",
                project_ids=[],
            )
        raise UnauthorizedError()

    getAdminInfo = mock_getAdminUserInfo


async def getUserOrgId(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
) -> str:
    """Return the authenticated user's organization id from token context."""
    return user_info["org_id"]


async def requireUserOrgId(
    org_id: Annotated[str, Depends(getUserOrgId)],
) -> str:
    """Return token org id, failing if the token has no organization context."""
    if not org_id:
        raise MissingOrganizationContextError()
    return org_id


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
