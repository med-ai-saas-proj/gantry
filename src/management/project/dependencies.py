"""FastAPI dependencies for project permissions."""

from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo

from .factories import ProjectService, getProjectService
from .permissions import ProjectPermission

from typing import Annotated

from fastapi import Path, Depends


def requiredProjectPermission(
    permission: ProjectPermission, allow_archived: bool = False
):
    """Return dependency enforcing project permission for path project_id."""

    async def _dependency(
        project_id: Annotated[str, Path()],
        user_info: Annotated[UserInfo, Depends(getUserInfo)],
        project_service: Annotated[ProjectService, Depends(getProjectService)],
    ) -> UserInfo:
        authz_res = await project_service.authorizeProjectPermission(
            project_uuid=project_id,
            user_id=user_info["id"],
            required=permission,
            allow_archived=allow_archived,
        )
        authz_res.unwrap()
        return user_info

    return _dependency


def userHasRole(required_permissions: list[ProjectPermission]):
    """Return dependency enforcing all required project permissions."""

    async def _dependency(
        project_id: Annotated[str, Path()],
        user_info: Annotated[UserInfo, Depends(getUserInfo)],
        project_service: Annotated[ProjectService, Depends(getProjectService)],
    ) -> UserInfo:
        for permission in required_permissions:
            authz_res = await project_service.authorizeProjectPermission(
                project_uuid=project_id,
                user_id=user_info["id"],
                required=permission,
            )
            authz_res.unwrap()
        return user_info

    return _dependency
