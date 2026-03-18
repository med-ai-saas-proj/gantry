"""FastAPI dependencies for authentication and authorization."""

from src.shared.custom_types.error_exception import RecoverableError
from src.management.organization.factories import (
    KeycloakOrgClient,
    getKeycloakOrgClient,
)

from .roles import ManagementRole
from .entities import UserInfo
from .settings import getAuthSettings
from .factories import AuthService, getAuthService

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer


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


class MissingOrganizationContextError(RecoverableError):
    """Raised when the authenticated token has no organization context."""

    status = 403
    code = "missing_org_context"
    title = "Missing Organization Context"
    detail = "The authenticated token does not include an organization id."


async def getUserInfo(
    token: Annotated[str, Security(oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAuthService)],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
) -> UserInfo:
    """
    Get authenticated user info from JWT token.

    This is the base dependency for authentication.
    Returns UserInfo if token is valid, raises UnauthorizedError otherwise.
    """
    user_info = auth_service.verifyToken(token).unwrap()
    user_info["org_id"] = user_info.get("org_id")

    if user_info.get("org_id") or user_info.get("is_service_account"):
        return user_info

    orgs_res = await kc_org_client.get_member_organizations(user_info["id"])
    if orgs_res.is_err():
        return user_info

    organizations = orgs_res.unwrap()
    for org in organizations:
        org_id = org.get("id")
        if isinstance(org_id, str) and org_id:
            user_info["org_id"] = org_id
            break

    return user_info


async def getUserOrgId(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
) -> str | None:
    """Return the authenticated user's organization id from token context."""
    return user_info.get("org_id")


async def requireUserOrgId(
    org_id: Annotated[str | None, Depends(getUserOrgId)],
) -> str:
    """Return token org id, failing if the token has no organization context."""
    if not org_id:
        raise MissingOrganizationContextError()
    return org_id


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
