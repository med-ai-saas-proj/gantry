"""FastAPI dependencies for the Organization module."""

from gantry.keycloak import getKeycloakSettings
from gantry.management.auth import (
    UserInfo,
    getUserInfo,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .services import InvalidPermissionError
from .settings import getOrgSettings
from .factories import OrgService, getOrgService
from .permissions import OrgPermission, has_permission

from typing import Annotated

from fastapi import Path, Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer


keycloak_settings = getKeycloakSettings()
server_url_str = keycloak_settings.server_url.encoded_string()
realm_name = keycloak_settings.realm_name
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


async def getLimit(
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> int | None:
    """Return effective org limit (org override or global default)."""
    settings_res = (await org_service.getSettings(org_id)).unwrap()
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


def _raise_permission_fetch_error(err: Exception):
    err_status = getattr(err, "status", 500)
    err_code = getattr(err, "code", "")
    if err_status >= 500:
        err_detail = getattr(err, "detail", str(err))
        wrapped = _KeycloakOrgError()
        wrapped.detail = (
            "Could not fetch organisation permissions from Keycloak. "
            f"{err_detail}"
        )
        return wrapped

    if err_code in {"member_not_found", "user_not_in_organization"}:
        return _InsufficientOrgPermission()

    return err


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
        user_info: Annotated[UserInfo, Depends(getUserInfo)],
    ) -> UserInfo:
        if not has_permission(user_info["org_permissions"], permission):
            raise _InsufficientOrgPermission()
        return user_info

    return _dependency
