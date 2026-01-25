"""Routes for permission management."""

from .permission_dtos import (
    CreatePermissionInput,
    UpdatePermissionInput,
    PermissionOutput,
    PermissionListOutput,
)
from .permission_service import PermissionService
from .factories import getPermissionService
from ..auth.dependencies import UserInfo, getUserInfo

from typing import Annotated

from fastapi import Body, Path, Query, Depends, APIRouter


permission_router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
    include_in_schema=True,
)


@permission_router.post("", tags=["permissions"])
async def createPermission(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    input: Annotated[CreatePermissionInput, Body()],
    permission_service: Annotated[
        PermissionService, Depends(getPermissionService)
    ],
) -> PermissionOutput:
    """Create a new permission."""
    result = await permission_service.createPermission(
        input.name, input.description
    )
    return result.unwrap()


@permission_router.get("", tags=["permissions"])
async def getPermissions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    permission_service: Annotated[
        PermissionService, Depends(getPermissionService)
    ],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PermissionListOutput:
    """Get all permissions with pagination."""
    result = await permission_service.getPermissions(skip, limit)
    return result.unwrap()


@permission_router.get("/{permission_id}", tags=["permissions"])
async def getPermissionById(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    permission_id: Annotated[
        int, Path(title="The ID of the permission to retrieve")
    ],
    permission_service: Annotated[
        PermissionService, Depends(getPermissionService)
    ],
) -> PermissionOutput:
    """Get a permission by ID."""
    result = await permission_service.getPermissionById(permission_id)
    return result.unwrap()


@permission_router.put("/{permission_id}", tags=["permissions"])
async def updatePermission(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    permission_id: Annotated[
        int, Path(title="The ID of the permission to update")
    ],
    input: Annotated[UpdatePermissionInput, Body()],
    permission_service: Annotated[
        PermissionService, Depends(getPermissionService)
    ],
) -> PermissionOutput:
    """Update a permission's description."""
    result = await permission_service.updatePermission(
        permission_id, input.description
    )
    return result.unwrap()


@permission_router.delete("/{permission_id}", tags=["permissions"])
async def deletePermission(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    permission_id: Annotated[
        int, Path(title="The ID of the permission to delete")
    ],
    permission_service: Annotated[
        PermissionService, Depends(getPermissionService)
    ],
):
    """Delete a permission if it's not in use."""
    result = await permission_service.deletePermission(permission_id)
    return result.unwrap()
