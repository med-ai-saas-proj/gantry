"""FastAPI dependencies for project permissions."""

from gantry.management.auth import UserInfo, getUserInfo

from .services import (
    ProjectArchivedError,
    UserNotInProjectError,
    InsufficientProjectPermissionError,
)
from .factories import ProjectService, getProjectService
from .permissions import (
    ProjectPermission,
    get_effective_permissions,
)

from typing import Annotated

from fastapi import Path, Depends


async def assertProjectRole(
    project_service: ProjectService,
    project_uuid: str,
    required_permissions: list[ProjectPermission],
    user_info: UserInfo,
    allow_archived: bool = False,
):
    if (
        await project_service.isProjectArchived(project_uuid)
        and not allow_archived
    ):
        raise ProjectArchivedError()
    try:
        effective_perms = get_effective_permissions(
            user_info["project_permissions"][project_uuid]
        )
    except KeyError as e:
        raise UserNotInProjectError() from e

    if not effective_perms.issuperset(required_permissions):
        raise InsufficientProjectPermissionError()
    pass


def requiredProjectPermission(
    permission: ProjectPermission, allow_archived: bool = False
):
    """Return dependency enforcing project permission for path project_id."""

    async def _dependency(
        project_id: Annotated[str, Path()],
        user_info: Annotated[UserInfo, Depends(getUserInfo)],
        project_service: Annotated[ProjectService, Depends(getProjectService)],
    ) -> UserInfo:
        await assertProjectRole(
            project_service, project_id, [permission], user_info, allow_archived
        )
        return user_info

    return _dependency


def userHasRole(
    required_permissions: list[ProjectPermission], allow_archived: bool = False
):
    """Return dependency enforcing all required project permissions."""

    async def _dependency(
        project_id: Annotated[str, Path()],
        user_info: Annotated[UserInfo, Depends(getUserInfo)],
        project_service: Annotated[ProjectService, Depends(getProjectService)],
    ) -> UserInfo:
        await assertProjectRole(
            project_service,
            project_id,
            required_permissions,
            user_info,
            allow_archived,
        )
        return user_info

    return _dependency
