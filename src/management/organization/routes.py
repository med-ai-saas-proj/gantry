"""
API routes for the Organization module.
"""

from src.management.auth.entities import UserInfo

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
)
from .factories import OrgService, getOrgService
from .permissions import OrgPermission
from .dependencies import _get_user_info, requiredOrgPermission

from typing import Annotated

from fastapi import Body, Path, Depends, Response, APIRouter


org_router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


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
    """Return metadata for the requested organization."""
    result = await org_service.get_org_info(org_id)
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
    """Update basic organization metadata."""
    result = await org_service.update_org_info(
        org_id=org_id,
        actor_user_id=user_info["id"],
        name=input_data.name,
        actor_is_service_account=bool(user_info.get("is_service_account")),
        actor_client_id=user_info.get("client_id"),
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
    """Create an organization delete request."""
    result = await org_service.request_delete_org(org_id)
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
    """Cancel an existing organization deletion request."""
    result = await org_service.cancel_delete_org(org_id)
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
    """Return organization settings."""
    result = await org_service.get_settings(org_id)
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
    """Update organization settings."""
    result = await org_service.update_settings(
        org_id, input_data.rate_limit, input_data.extra
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
    """List users in the organization."""
    result = await org_service.get_users(
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
    """Remove a user from the organization and delete the account."""
    result = await org_service.remove_user(org_id, user_id)
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
    """List invitations for the organization."""
    result = await org_service.get_invitations(org_id)
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
    """Invite a user to join the organization."""
    result = await org_service.create_invitation(
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
    """Return details for a single invitation."""
    result = await org_service.get_invitation(org_id, invitation_id)
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
    """Delete an invitation."""
    result = await org_service.delete_invitation(org_id, invitation_id)
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
    """Resend an invitation email."""
    result = await org_service.resend_invitation(org_id, invitation_id)
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
    """Return organization permissions for a user."""
    authz_res = await org_service.ensure_can_read_user_permissions(
        org_id=org_id,
        actor_user_id=user_info["id"],
        target_user_id=user_id,
        actor_is_service_account=bool(user_info.get("is_service_account")),
        actor_client_id=user_info.get("client_id"),
    )
    authz_res.unwrap()
    result = await org_service.get_user_permissions(org_id, user_id)
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
    """Replace organization permissions for a user."""
    result = await org_service.update_user_permissions(
        org_id=org_id,
        actor_user_id=user_info["id"],
        user_id=user_id,
        permissions=input_data.permissions,
        actor_is_service_account=bool(user_info.get("is_service_account")),
        actor_client_id=user_info.get("client_id"),
    )
    return result.unwrap()
