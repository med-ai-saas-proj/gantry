"""FastAPI dependencies for authentication and authorization."""

from gantry.settings import AppStage, getAppSettings
from gantry.management.organization.factories import (
    KeycloakOrgClient,
    getKeycloakOrgClient,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .roles import ManagementRole
from .entities import UserInfo
from .settings import getAuthSettings
from .factories import AuthService, getAuthService

from typing import Any, Annotated

from fastapi import Depends, Security
from pyrusult import ResultStatus
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


app_settings = getAppSettings()


def _get_project_service():
    """Lazy import project service factory to avoid auth/project cycles."""
    from gantry.management.project.factories import getProjectService

    return getProjectService()


async def _getUserInfo(
    token: Annotated[str, Security(oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAuthService)],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
    project_service: Annotated[Any, Depends(_get_project_service)],
) -> UserInfo:
    """
    Get authenticated user info from JWT token.

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

    if user_info["org_id"]:
        projects_res = await project_service.listAccessibleProjects(
            actor_user_id=user_info["id"],
            organization_id=user_info["org_id"],
        )
        if projects_res.status == ResultStatus.Ok:
            user_info["projects"] = [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "organization_id": project.organization_id,
                    "archived": project.archived,
                }
                for project in projects_res.unwrap().results
            ]
        else:
            user_info["projects"] = []

    return user_info


getUserInfo = _getUserInfo

# if app_settings.stage == AppStage.DEV:
#     from gantry.management.auth.services import UnauthorizedError

#     from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

#     # If mock_auth is enabled, bypass all auth checks and return a dummy UserInfo
#     security = HTTPBearer()

#     async def mock_getUserInfo(
#         auth: Annotated[HTTPAuthorizationCredentials, Depends(security)],
#         auth_service: Annotated[AuthService, Depends(getAuthService)],
#     ) -> UserInfo:
#         if auth.credentials == "bypass_token":
#             return UserInfo(
#                 id="test_user",
#                 username="test_user",
#                 email="test_user@example.com",
#                 roles=[],
#                 org_id="test_org1",
#             )
#         raise UnauthorizedError()

#     getUserInfo = mock_getUserInfo


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
