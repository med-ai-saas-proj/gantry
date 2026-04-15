"""
API routes for the Organization module.
"""

from gantry.management.auth.entities import UserInfo

from .dtos import (
    PaginatedQuery,
    OrgInfoResponse,
    InviteUserRequest,
    InvitationResponse,
    OrgSettingsResponse,
    OrgUserListResponse,
    DeleteCancelResponse,
    DeleteRequestResponse,
    UpdateSettingsRequest,
    InvitationListResponse,
    UserPermissionsRequest,
    UserPermissionsResponse,
    UpdateOrgMetadataRequest,
    PermissionCatalogResponse,
)
from .factories import OrgService, getOrgService
from .permissions import ALL_PERMISSIONS, OrgPermission
from .dependencies import _get_user_info, requiredOrgPermission

from typing import Annotated

from fastapi import Body, Path, Depends, Response, APIRouter


org_router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


@org_router.get(
    "/permissions",
    response_model=PermissionCatalogResponse,
    summary="List all organization permissions",
)
async def list_org_permissions() -> PermissionCatalogResponse:
    """Return the full organization permission catalog for UI consumers."""
    return PermissionCatalogResponse(permissions=ALL_PERMISSIONS)


@org_router.get(
    "/{org_id}",
    response_model=OrgInfoResponse,
    summary="Get organization metadata",
)
async def get_org_info(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.SETTINGS_READ)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> OrgInfoResponse:
    """Return organization metadata after permission checks pass."""
    result = await org_service.getOrgInfo(org_id)
    return result.unwrap()


@org_router.patch(
    "/{org_id}",
    response_model=OrgInfoResponse,
    summary="Update organization metadata",
)
async def update_org_info(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.OWNER)),
    ],
    org_id: Annotated[str, Path()],
    input_data: Annotated[UpdateOrgMetadataRequest, Body()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> OrgInfoResponse:
    """Rename an organization using the current authorized actor."""
    result = await org_service.updateOrgInfo(
        org_id=org_id,
        actor_user_id=user_info["id"],
        name=input_data.name,
    )
    return result.unwrap()


@org_router.delete(
    "/{org_id}",
    status_code=202,
    response_model=DeleteRequestResponse,
    summary="Request organization deletion",
)
async def delete_org(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.OWNER)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> DeleteRequestResponse:
    """Create a delayed organization deletion request."""
    result = await org_service.requestDeleteOrg(org_id)
    return result.unwrap()


@org_router.post(
    "/{org_id}/deletion/cancel",
    response_model=DeleteCancelResponse,
    summary="Cancel organization deletion request",
)
async def cancel_delete_org(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.OWNER)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> DeleteCancelResponse:
    """Cancel a previously requested organization deletion."""
    result = await org_service.cancelDeleteOrg(org_id)
    result.unwrap()
    return DeleteCancelResponse(org_id=org_id, cancelled=True)


@org_router.get(
    "/{org_id}/settings",
    response_model=OrgSettingsResponse,
    summary="Get org settings",
)
async def get_settings(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.SETTINGS_READ)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> OrgSettingsResponse:
    """Return the effective persisted settings for one organization."""
    result = await org_service.getSettings(org_id)
    return result.unwrap()


@org_router.patch(
    "/{org_id}/settings",
    response_model=OrgSettingsResponse,
    summary="Update org settings",
)
async def update_settings(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.SETTINGS_WRITE)),
    ],
    org_id: Annotated[str, Path()],
    input_data: Annotated[UpdateSettingsRequest, Body()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> OrgSettingsResponse:
    """Replace organization settings with the submitted payload."""
    result = await org_service.updateSettings(
        org_id,
        input_data.rate_limit,
        input_data.spending_limit,
        input_data.extra,
    )
    return result.unwrap()


@org_router.get(
    "/{org_id}/users",
    response_model=OrgUserListResponse,
    summary="Get all users in this org",
)
async def get_users(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.USERS_GET_ALL)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
    pagination: Annotated[PaginatedQuery, Depends()],
) -> OrgUserListResponse:
    """List organization members with pagination and search."""
    result = await org_service.getUsers(
        org_id,
        limit=pagination.limit,
        offset=pagination.offset,
        q=pagination.q,
    )
    return result.unwrap()


@org_router.delete(
    "/{org_id}/users/{user_id}",
    summary="Kick user and delete account",
)
async def remove_user(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.USERS_REMOVE)),
    ],
    org_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> Response:
    """Remove a member from the organization and delete the user account."""
    result = await org_service.removeUser(org_id, user_id)
    result.unwrap()
    return Response(status_code=200)


@org_router.get(
    "/{org_id}/invitations",
    response_model=InvitationListResponse,
    summary="List all invitations",
)
async def get_invitations(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.INVITE)),
    ],
    org_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> InvitationListResponse:
    """List current invitations for the organization."""
    result = await org_service.getInvitations(org_id)
    return result.unwrap()


@org_router.post(
    "/{org_id}/invitations",
    summary="Invite a user to the org",
)
async def invite_user(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.INVITE)),
    ],
    org_id: Annotated[str, Path()],
    input_data: Annotated[InviteUserRequest, Body()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> Response:
    """Create and send an invitation to join the organization."""
    result = await org_service.createInvitation(
        org_id,
        input_data.email,
    )
    result.unwrap()
    return Response(status_code=200)


@org_router.get(
    "/{org_id}/invitations/{invitation_id}",
    response_model=InvitationResponse,
    summary="Get invitation details",
)
async def get_invitation(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.INVITE)),
    ],
    org_id: Annotated[str, Path()],
    invitation_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> InvitationResponse:
    """Return details for one organization invitation."""
    result = await org_service.getInvitation(org_id, invitation_id)
    return result.unwrap()


@org_router.delete(
    "/{org_id}/invitations/{invitation_id}",
    summary="Cancel an invitation",
)
async def delete_invitation(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.INVITE)),
    ],
    org_id: Annotated[str, Path()],
    invitation_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> Response:
    """Delete one organization invitation."""
    result = await org_service.deleteInvitation(org_id, invitation_id)
    result.unwrap()
    return Response(status_code=200)


@org_router.post(
    "/{org_id}/invitations/{invitation_id}/resend",
    summary="Resend an invitation",
)
async def resend_invitation(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.INVITE)),
    ],
    org_id: Annotated[str, Path()],
    invitation_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> Response:
    """Resend the invitation email for one invitation."""
    result = await org_service.resendInvitation(org_id, invitation_id)
    result.unwrap()
    return Response(status_code=200)


@org_router.get(
    "/{org_id}/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Get user org permissions",
)
async def get_user_permissions(
    user_info: Annotated[
        UserInfo,
        Depends(_get_user_info),
    ],
    org_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> UserPermissionsResponse:
    """Return organization permissions for the target user."""
    authz_res = await org_service.ensureCanReadUserPermissions(
        org_id=org_id,
        actor_user_id=user_info["id"],
        target_user_id=user_id,
    )
    authz_res.unwrap()
    result = await org_service.getUserPermissions(org_id, user_id)
    return result.unwrap()


@org_router.put(
    "/{org_id}/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Update user org permissions",
)
async def update_user_permissions(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.USERS_PERMISSIONS_RW)),
    ],
    org_id: Annotated[str, Path()],
    user_id: Annotated[str, Path()],
    input_data: Annotated[UserPermissionsRequest, Body()],
    org_service: Annotated[OrgService, Depends(getOrgService)],
) -> UserPermissionsResponse:
    """Replace the target user's organization permissions."""
    result = await org_service.updateUserPermissions(
        org_id=org_id,
        actor_user_id=user_info["id"],
        user_id=user_id,
        permissions=input_data.permissions,
    )
    return result.unwrap()
