"""FastAPI dependencies for project permissions."""

from gantry.management.auth import UserInfo, getUserInfo
from gantry.management.organization import OrgPermission
from gantry.management.auth.entities import UserInfoWithProjectContext

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

import enum
from uuid import UUID
from typing import Annotated

from fastapi import Path, Query, Depends


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
    if OrgPermission.OWNER.value in user_info["org_permissions"]:
        return
    try:
        effective_perms = get_effective_permissions(
            user_info["project_permissions"][project_uuid]
        )
    except KeyError as e:
        raise UserNotInProjectError() from e

    if not effective_perms.issuperset(required_permissions):
        raise InsufficientProjectPermissionError()
    pass


class ProjectExtractFrom(enum.Enum, str):
    PATH = "path"
    QUERY = "query"


def requiredProjectPermission(
    permission: ProjectPermission,
    allow_archived: bool = False,
    extract_from: ProjectExtractFrom = ProjectExtractFrom.PATH,
):
    """Return dependency enforcing project permission for path project_uuid."""

    if extract_from == ProjectExtractFrom.PATH:

        async def _dependency(
            user_info: Annotated[UserInfo, Depends(getUserInfo)],
            project_service: Annotated[
                ProjectService, Depends(getProjectService)
            ],
            project_uuid: UUID = Path(..., description="Project UUID"),
        ) -> UserInfoWithProjectContext:
            await assertProjectRole(
                project_service,
                str(project_uuid),
                [permission],
                user_info,
                allow_archived,
            )
            return {
                **user_info,
                "project_uuid": project_uuid,
            }

        return _dependency

    elif extract_from == ProjectExtractFrom.QUERY:

        async def _dependency(
            user_info: Annotated[UserInfo, Depends(getUserInfo)],
            project_service: Annotated[
                ProjectService, Depends(getProjectService)
            ],
            project_uuid: UUID = Query(..., description="Project UUID"),
        ) -> UserInfoWithProjectContext:
            await assertProjectRole(
                project_service,
                str(project_uuid),
                [permission],
                user_info,
                allow_archived,
            )
            return {
                **user_info,
                "project_uuid": project_uuid,
            }

        return _dependency

    else:
        raise ValueError("Invalid extract_from value")


def userHasRole(
    required_permissions: list[ProjectPermission],
    allow_archived: bool = False,
    extract_from: ProjectExtractFrom = ProjectExtractFrom.PATH,
):
    """Return dependency enforcing all required project permissions."""

    if extract_from == ProjectExtractFrom.PATH:

        async def _dependency(
            user_info: Annotated[UserInfo, Depends(getUserInfo)],
            project_service: Annotated[
                ProjectService, Depends(getProjectService)
            ],
            project_uuid: UUID = Path(..., description="Project UUID"),
        ) -> UserInfoWithProjectContext:
            await assertProjectRole(
                project_service,
                str(project_uuid),
                required_permissions,
                user_info,
                allow_archived,
            )
            return {
                **user_info,
                "project_uuid": project_uuid,
            }

        return _dependency

    elif extract_from == ProjectExtractFrom.QUERY:

        async def _dependency(
            user_info: Annotated[UserInfo, Depends(getUserInfo)],
            project_service: Annotated[
                ProjectService, Depends(getProjectService)
            ],
            project_uuid: UUID = Query(..., description="Project UUID"),
        ) -> UserInfoWithProjectContext:
            await assertProjectRole(
                project_service,
                str(project_uuid),
                required_permissions,
                user_info,
                allow_archived,
            )
            return {
                **user_info,
                "project_uuid": project_uuid,
            }

        return _dependency

    else:
        raise ValueError("Invalid extract_from value")
