"""FastAPI dependencies for the Organization module."""

from src.management.auth.entities import UserInfo
from src.management.auth.settings import getAuthSettings
from src.management.auth.factories import AuthService, getAuthService
from src.shared.custom_types.error_exception import RecoverableError

from .services import InvalidPermissionError
from .settings import getOrgSettings
from .factories import OrgService, getOrgService
from .permissions import OrgPermission, has_permission

from typing import Annotated

from fastapi import Path, Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer


auth_settings = getAuthSettings()
server_url_str = auth_settings.server_url.encoded_string()
realm_name = auth_settings.realm_name
org_settings = getOrgSettings()

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


async def _get_user_info(
    token: Annotated[str, Security(oauth_2_scheme)],
    auth_service: Annotated[AuthService, Depends(getAuthService)],
) -> UserInfo:
    """Verify the JWT and return ``UserInfo``."""
    return auth_service.verifyToken(token).unwrap()


async def getLimit(
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> int | None:
    """Return effective org limit (org override or global default)."""
    settings_res = (await org_service.get_settings(org_id)).unwrap()
    org_limit = settings_res.rate_limit
    if org_limit is not None:
        return org_limit
    return org_settings.default_rate_limit


class _InsufficientOrgPermission(InvalidPermissionError):
    status = 403
    code = "insufficient_org_permission"
    title = "Insufficient Organization Permission"
    detail = "You do not have the required organization permission."


class _KeycloakOrgError(RecoverableError):
    status = 502
    code = "keycloak_error"
    title = "Keycloak Error"
    detail = "Could not fetch organisation permissions from Keycloak."


def _raise_permission_fetch_error(err: Exception) -> None:
    err_status = getattr(err, "status", 500)
    err_code = getattr(err, "code", "")
    if err_status >= 500:
        err_detail = getattr(err, "detail", str(err))
        wrapped = _KeycloakOrgError()
        wrapped.detail = (
            "Could not fetch organisation permissions from Keycloak. "
            f"{err_detail}"
        )
        raise wrapped

    if err_code in {"member_not_found", "user_not_in_organization"}:
        raise _InsufficientOrgPermission()

    raise err


async def _get_permissions_or_raise(
    org_service: OrgService,
    org_id: str,
    user_id: str,
) -> list[str]:
    perms_res = await org_service.get_user_permissions(org_id, user_id)
    if perms_res.is_err():
        _raise_permission_fetch_error(perms_res.error)
    return perms_res.unwrap().permissions


def requiredOrgPermission(permission: OrgPermission):
    """Return a dependency that enforces *permission* for the org.

    The ``org_id`` is taken from the path parameter of the same name.
    Organisation-level permissions are stored as a Keycloak user
    attribute (``org_permissions``) and checked on every request.

    Usage::

        @router.get(
            "/{org_id}/users"
        )
        async def list_users(
            user_info: Annotated[
                UserInfo,
                Depends(
                    requiredOrgPermission(
                        OrgPermission.USERS_GET_ALL
                    )
                ),
            ],
        ): ...
    """

    async def _dependency(
        org_id: Annotated[str, Path()],
        user_info: Annotated[UserInfo, Depends(_get_user_info)],
        org_service: Annotated[OrgService, Depends(getOrgService)],
    ) -> UserInfo:
        user_perms = await _get_permissions_or_raise(
            org_service, org_id, user_info["id"]
        )
        if not has_permission(user_perms, permission):
            raise _InsufficientOrgPermission()
        return user_info

    return _dependency
