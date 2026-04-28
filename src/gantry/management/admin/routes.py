"""Admin-only management routes."""

from gantry.management.auth import UserInfo, getAdminUserInfo
from gantry.management.project.permissions import (
    ALL_PERMISSIONS as ALL_PROJECT_PERMISSIONS,
)
from gantry.management.organization.factories import (
    KeycloakOrgClient,
    getKeycloakOrgClient,
)
from gantry.management.organization.permissions import (
    ALL_PERMISSIONS as ALL_ORG_PERMISSIONS,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .dtos import (
    AdminUserInfoResponse,
    AdminUserProfileResponse,
    AdminUserPermissionUpdateRequest,
    AdminUserOrganizationInfoResponse,
    AdminUserProjectPermissionUpdateRequest,
)
from .permissions import (
    ORG_PERMISSIONS_ATTR,
    PROJECT_PERMISSIONS_ATTR,
    build_permission_summary,
    flatten_project_permission_updates,
)

from typing import Annotated

from fastapi import Body, Path, Depends, APIRouter


admin_router = APIRouter(prefix="/admin", tags=["admin"])


class InvalidAdminPermissionError(RecoverableError):
    """Raised when admin payload contains unknown org/project permissions."""

    status = 400
    code = "invalid_permission"
    title = "Invalid Permission"
    detail = "One or more permission strings are invalid."


def _validate_permission_update_payload(
    payload: AdminUserPermissionUpdateRequest,
) -> None:
    """Fail fast if any organization or project permission is unknown."""
    invalid_org_permissions = sorted(
        {
            permission
            for permission in payload.organization_permissions
            if permission not in ALL_ORG_PERMISSIONS
        }
    )
    if invalid_org_permissions:
        error = InvalidAdminPermissionError()
        error.detail = "Invalid organization permissions: " + ", ".join(
            invalid_org_permissions
        )
        raise error

    invalid_project_permissions = sorted(
        {
            permission
            for item in payload.project_permissions
            for permission in item.permissions
            if permission not in ALL_PROJECT_PERMISSIONS
        }
    )
    if invalid_project_permissions:
        error = InvalidAdminPermissionError()
        error.detail = "Invalid project permissions: " + ", ".join(
            invalid_project_permissions
        )
        raise error


async def _build_user_profile_response(
    user_id: str,
    kc_org_client: KeycloakOrgClient,
) -> AdminUserProfileResponse:
    """Load one user's Keycloak profile and map it into the admin response."""
    profile_res = await kc_org_client.getUserProfile(user_id)
    profile = profile_res.unwrap()

    orgs_res = await kc_org_client.getMemberOrganizations(user_id)
    organizations = orgs_res.unwrap()

    attrs = profile.get("attributes", {})
    if not isinstance(attrs, dict):
        attrs = {}

    return AdminUserProfileResponse(
        id=str(profile["id"]),
        username=profile.get("username"),
        email=profile.get("email"),
        first_name=profile.get("firstName"),
        last_name=profile.get("lastName"),
        enabled=bool(profile.get("enabled", False)),
        email_verified=bool(profile.get("emailVerified", False)),
        organizations=[
            AdminUserOrganizationInfoResponse(
                id=str(org["id"]),
                name=org.get("name"),
                alias=org.get("alias"),
            )
            for org in organizations
            if isinstance(org.get("id"), str)
        ],
        permissions=build_permission_summary(attrs),
    )


@admin_router.get(
    "/me",
    response_model=AdminUserInfoResponse,
    summary="Get authenticated admin user info",
)
async def get_admin_me(
    user_info: Annotated[UserInfo, Depends(getAdminUserInfo)],
) -> AdminUserInfoResponse:
    """Return the current admin user after ADMIN realm-role verification."""
    return AdminUserInfoResponse(
        id=user_info["id"],
        username=user_info["username"],
        email=user_info["email"],
        roles=user_info["roles"],
    )


@admin_router.get(
    "/users/{user_id}/organizations",
    response_model=list[AdminUserOrganizationInfoResponse],
    summary="List organizations for a specific user",
)
async def get_user_organizations(
    user_info: Annotated[UserInfo, Depends(getAdminUserInfo)],
    user_id: Annotated[str, Path()],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
) -> list[AdminUserOrganizationInfoResponse]:
    """Return organization memberships for any user after admin auth."""
    del user_info
    result = await kc_org_client.getMemberOrganizations(user_id)
    organizations = result.unwrap()
    return [
        AdminUserOrganizationInfoResponse(
            id=str(org["id"]),
            name=org.get("name"),
            alias=org.get("alias"),
        )
        for org in organizations
        if isinstance(org.get("id"), str)
    ]


@admin_router.get(
    "/users/{user_id}/profile",
    response_model=AdminUserProfileResponse,
    summary="Get Keycloak profile and permissions for a specific user",
)
async def get_user_profile(
    user_info: Annotated[UserInfo, Depends(getAdminUserInfo)],
    user_id: Annotated[str, Path()],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
) -> AdminUserProfileResponse:
    """Return one user's Keycloak profile plus normalized permission data."""
    del user_info
    return await _build_user_profile_response(user_id, kc_org_client)


@admin_router.put(
    "/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Replace Keycloak org/project permissions for a specific user",
)
async def set_user_permissions(
    user_info: Annotated[UserInfo, Depends(getAdminUserInfo)],
    user_id: Annotated[str, Path()],
    payload: Annotated[AdminUserPermissionUpdateRequest, Body()],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
) -> AdminUserProfileResponse:
    """Replace one user's permission attributes through Keycloak admin API."""
    del user_info
    _validate_permission_update_payload(payload)
    update_res = await kc_org_client.setUserAttributes(
        user_id,
        {
            ORG_PERMISSIONS_ATTR: payload.organization_permissions,
            PROJECT_PERMISSIONS_ATTR: flatten_project_permission_updates(
                payload.project_permissions
            ),
        },
    )
    update_res.unwrap()
    return await _build_user_profile_response(user_id, kc_org_client)


@admin_router.delete(
    "/users/{user_id}/permissions",
    response_model=AdminUserProfileResponse,
    summary="Reset Keycloak org/project permissions for a specific user",
)
async def reset_user_permissions(
    user_info: Annotated[UserInfo, Depends(getAdminUserInfo)],
    user_id: Annotated[str, Path()],
    kc_org_client: Annotated[KeycloakOrgClient, Depends(getKeycloakOrgClient)],
) -> AdminUserProfileResponse:
    """Clear one user's org/project permission attributes in Keycloak."""
    del user_info
    update_res = await kc_org_client.setUserAttributes(
        user_id,
        {
            ORG_PERMISSIONS_ATTR: [],
            PROJECT_PERMISSIONS_ATTR: {},
        },
    )
    update_res.unwrap()
    return await _build_user_profile_response(user_id, kc_org_client)
