"""Business logic for project management."""

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError
from src.management.organization.keycloak_client import (
    KeycloakOrgClient,
    UserNotInOrganizationError,
)

from .dtos import (
    ProjectInfoResponse,
    ProjectListResponse,
    ProjectUserResponse,
    ProjectArchiveResponse,
    ProjectUserListResponse,
    ProjectUserPermissionsResponse,
)
from .permissions import ProjectPermission, has_permission
from .repositories import ProjectRepository, ProjectMembershipRepository

from safe_result import Ok, Err, Result
from structlog.stdlib import BoundLogger


class InvalidProjectPermissionError(RecoverableError):
    status = 400
    code = "invalid_project_permission"
    title = "Invalid Project Permission"
    detail = "One or more project permissions are invalid."


class ProjectNotFoundError(RecoverableError):
    status = 404
    code = "project_not_found"
    title = "Project Not Found"
    detail = "The specified project does not exist."


class UserNotInProjectError(RecoverableError):
    status = 404
    code = "user_not_in_project"
    title = "User Not In Project"
    detail = "The user is not a member of this project."


class UserAlreadyInProjectError(RecoverableError):
    status = 409
    code = "user_already_in_project"
    title = "User Already In Project"
    detail = "The user is already a member of this project."


class InsufficientProjectPermissionError(RecoverableError):
    status = 403
    code = "insufficient_project_permission"
    title = "Insufficient Project Permission"
    detail = "You do not have the required project permission."


class ProjectArchivedError(RecoverableError):
    status = 409
    code = "project_archived"
    title = "Project Archived"
    detail = "This project is archived and can no longer be modified."


class OwnerRequiredForGrantError(RecoverableError):
    status = 403
    code = "owner_required_for_permission_grant"
    title = "Owner Required"
    detail = (
        "Only project owner can grant project.users.permissions.read_write."
    )


class LastOwnerRemovalNotAllowedError(RecoverableError):
    status = 403
    code = "last_owner_removal_not_allowed"
    title = "Last Owner Removal Not Allowed"
    detail = "A project must have at least one owner."


class ProjectService:
    """Project feature service."""

    def __init__(
        self,
        session_manager: AsyncSessionManager,
        logger: BoundLogger,
        project_repo: ProjectRepository,
        membership_repo: ProjectMembershipRepository,
        kc_client: KeycloakOrgClient,
    ):
        self.session_manager = session_manager
        self.logger = logger
        self.project_repo = project_repo
        self.membership_repo = membership_repo
        self.kc = kc_client

    async def _ensure_user_in_org(
        self,
        user_id: str,
        org_id: str,
    ) -> Result[None, RecoverableError]:
        orgs_res = await self.kc.get_member_organizations(user_id)
        if orgs_res.is_err():
            return orgs_res
        for org in orgs_res.unwrap():
            if str(org.get("id", "")) == org_id:
                return Ok(None)
        return Err(UserNotInOrganizationError())

    async def _get_project_or_err(
        self, project_uuid: str
    ) -> Result[tuple[int, str, ProjectInfoResponse], RecoverableError]:
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.get_by_uuid(session, project_uuid)
            if project is None:
                return Err(ProjectNotFoundError())
            return Ok(
                (
                    project.id,
                    project.organization_id,
                    ProjectInfoResponse(
                        id=str(project.uuid),
                        name=project.name,
                        description=project.description,
                        organization_id=project.organization_id,
                        archived=project.is_archived,
                    ),
                )
            )

    def _ensure_project_active(
        self,
        project_info: ProjectInfoResponse,
    ) -> Result[None, RecoverableError]:
        if project_info.archived:
            return Err(ProjectArchivedError())
        return Ok(None)

    async def _get_member_permissions(
        self,
        project_id: int,
        user_id: str,
    ) -> Result[list[str], RecoverableError]:
        async with self.session_manager.get_session() as session:
            member = await self.membership_repo.get_membership(
                session, project_id, user_id
            )
            if member is None:
                return Err(UserNotInProjectError())
            return Ok(member.permissions or [])

    async def authorize_project_permission(
        self,
        project_uuid: str,
        user_id: str,
        required: ProjectPermission,
        allow_archived: bool = False,
    ) -> Result[None, RecoverableError]:
        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, _, project_info = project_res.unwrap()
        if not allow_archived:
            active_res = self._ensure_project_active(project_info)
            if active_res.is_err():
                return active_res
        perms_res = await self._get_member_permissions(project_id, user_id)
        if perms_res.is_err():
            return perms_res
        if not has_permission(perms_res.unwrap(), required):
            return Err(InsufficientProjectPermissionError())
        return Ok(None)

    async def list_user_projects(
        self,
        actor_user_id: str,
        organization_id: str | None = None,
    ) -> Result[ProjectListResponse, RecoverableError]:
        if organization_id:
            member_res = await self._ensure_user_in_org(
                actor_user_id, organization_id
            )
            if member_res.is_err():
                return member_res

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.list_by_member(
                session, actor_user_id, organization_id=organization_id
            )
            return Ok(
                ProjectListResponse(
                    total=len(projects),
                    results=[
                        ProjectInfoResponse(
                            id=str(p.uuid),
                            name=p.name,
                            description=p.description,
                            organization_id=p.organization_id,
                            archived=p.is_archived,
                        )
                        for p in projects
                    ],
                )
            )

    async def _has_org_wide_project_permission(
        self,
        actor_user_id: str,
        organization_id: str,
        required: ProjectPermission,
    ) -> Result[bool, RecoverableError]:
        async with self.session_manager.get_session() as session:
            memberships = (
                await self.membership_repo.list_memberships_for_user_in_org(
                    session, actor_user_id, organization_id
                )
            )
            for membership in memberships:
                if has_permission(membership.permissions or [], required):
                    return Ok(True)
        return Ok(False)

    async def list_org_projects(
        self,
        actor_user_id: str,
        organization_id: str,
    ) -> Result[ProjectListResponse, RecoverableError]:
        authz_res = await self._has_org_wide_project_permission(
            actor_user_id, organization_id, ProjectPermission.PROJECTS_GET_ALL
        )
        if authz_res.is_err():
            return authz_res
        if not authz_res.unwrap():
            return Err(InsufficientProjectPermissionError())

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.list_by_org(
                session, organization_id
            )
            return Ok(
                ProjectListResponse(
                    total=len(projects),
                    results=[
                        ProjectInfoResponse(
                            id=str(p.uuid),
                            name=p.name,
                            description=p.description,
                            organization_id=p.organization_id,
                            archived=p.is_archived,
                        )
                        for p in projects
                    ],
                )
            )

    async def create_project(
        self,
        actor_user_id: str,
        organization_id: str,
        name: str,
        description: str | None,
    ) -> Result[ProjectInfoResponse, RecoverableError]:
        authz_res = await self._has_org_wide_project_permission(
            actor_user_id, organization_id, ProjectPermission.PROJECTS_CREATE
        )
        if authz_res.is_err():
            return authz_res
        if not authz_res.unwrap():
            return Err(InsufficientProjectPermissionError())

        async with self.session_manager.get_session() as session:
            project = await self.project_repo.create(
                session=session,
                name=name,
                description=description,
                organization_id=organization_id,
            )
            await self.membership_repo.upsert_membership(
                session=session,
                project_id=project.id,
                user_id=actor_user_id,
                permissions=[ProjectPermission.OWNER.value],
            )
            output = ProjectInfoResponse(
                id=str(project.uuid),
                name=project.name,
                description=project.description,
                organization_id=project.organization_id,
                archived=project.is_archived,
            )
            await session.commit()
            return Ok(output)

    async def list_project_users(
        self,
        project_uuid: str,
        offset: int = 0,
        limit: int = 20,
        q: str | None = None,
    ) -> Result[ProjectUserListResponse, RecoverableError]:
        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, org_id, project_info = project_res.unwrap()
        active_res = self._ensure_project_active(project_info)
        if active_res.is_err():
            return active_res

        async with self.session_manager.get_session() as session:
            members = await self.membership_repo.list_members(
                session, project_id
            )
            user_ids = {m.user_id for m in members}

        users_res = await self.kc.get_org_members(
            org_id,
            first=0,
            max_results=1000,
            search=q,
        )
        if users_res.is_err():
            return users_res
        users = users_res.unwrap()

        results = []
        for user in users:
            user_id = str(user.get("id", ""))
            if user_id in user_ids:
                results.append(
                    ProjectUserResponse(
                        id=user_id,
                        username=user.get("username"),
                        email=user.get("email"),
                    )
                )
        total = len(results)
        paged = results[offset : offset + limit]
        return Ok(ProjectUserListResponse(total=total, results=paged))

    async def add_user_to_project(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[bool, RecoverableError]:
        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, org_id, project_info = project_res.unwrap()
        active_res = self._ensure_project_active(project_info)
        if active_res.is_err():
            return active_res

        in_org_res = await self._ensure_user_in_org(target_user_id, org_id)
        if in_org_res.is_err():
            return in_org_res

        async with self.session_manager.get_session() as session:
            existing = await self.membership_repo.get_membership(
                session, project_id, target_user_id
            )
            if existing is not None:
                return Err(UserAlreadyInProjectError())
            await self.membership_repo.upsert_membership(
                session=session,
                project_id=project_id,
                user_id=target_user_id,
                permissions=[],
            )
            await session.commit()
            return Ok(True)

    async def remove_user_from_project(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[bool, RecoverableError]:
        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, _, project_info = project_res.unwrap()
        active_res = self._ensure_project_active(project_info)
        if active_res.is_err():
            return active_res

        async with self.session_manager.get_session() as session:
            membership = await self.membership_repo.get_membership(
                session, project_id, target_user_id
            )
            if membership is None:
                return Err(UserNotInProjectError())

            if ProjectPermission.OWNER.value in (membership.permissions or []):
                owner_count = await self.membership_repo.count_owners(
                    session, project_id, ProjectPermission.OWNER.value
                )
                if owner_count <= 1:
                    return Err(LastOwnerRemovalNotAllowedError())

            await self.membership_repo.delete_membership(
                session, project_id, target_user_id
            )
            await session.commit()
            return Ok(True)

    async def get_user_permissions(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[ProjectUserPermissionsResponse, RecoverableError]:
        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, _, project_info = project_res.unwrap()
        active_res = self._ensure_project_active(project_info)
        if active_res.is_err():
            return active_res

        perms_res = await self._get_member_permissions(
            project_id, target_user_id
        )
        if perms_res.is_err():
            return perms_res

        return Ok(
            ProjectUserPermissionsResponse(permissions=perms_res.unwrap())
        )

    async def update_user_permissions(
        self,
        project_uuid: str,
        actor_user_id: str,
        target_user_id: str,
        permissions: list[str],
    ) -> Result[ProjectUserPermissionsResponse, RecoverableError]:
        valid = {p.value for p in ProjectPermission}
        invalid = set(permissions) - valid
        if invalid:
            return Err(InvalidProjectPermissionError())

        project_res = await self._get_project_or_err(project_uuid)
        if project_res.is_err():
            return project_res
        project_id, _, project_info = project_res.unwrap()
        active_res = self._ensure_project_active(project_info)
        if active_res.is_err():
            return active_res

        actor_perms_res = await self._get_member_permissions(
            project_id, actor_user_id
        )
        if actor_perms_res.is_err():
            return actor_perms_res
        actor_perms = actor_perms_res.unwrap()

        if (
            ProjectPermission.USERS_PERMISSIONS_RW.value in permissions
            and not has_permission(actor_perms, ProjectPermission.OWNER)
        ):
            return Err(OwnerRequiredForGrantError())

        async with self.session_manager.get_session() as session:
            target = await self.membership_repo.get_membership(
                session, project_id, target_user_id
            )
            if target is None:
                return Err(UserNotInProjectError())

            is_removing_owner = (
                ProjectPermission.OWNER.value in (target.permissions or [])
                and ProjectPermission.OWNER.value not in permissions
            )
            if is_removing_owner:
                owner_count = await self.membership_repo.count_owners(
                    session, project_id, ProjectPermission.OWNER.value
                )
                if owner_count <= 1:
                    return Err(LastOwnerRemovalNotAllowedError())

            await self.membership_repo.upsert_membership(
                session,
                project_id=project_id,
                user_id=target_user_id,
                permissions=permissions,
            )
            await session.commit()
            return Ok(ProjectUserPermissionsResponse(permissions=permissions))

    async def set_project_archived(
        self,
        project_uuid: str,
        archived: bool,
    ) -> Result[ProjectArchiveResponse, RecoverableError]:
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.get_by_uuid(session, project_uuid)
            if project is None:
                return Err(ProjectNotFoundError())
            # Archived project is immutable except owner-triggered unarchive.
            if project.is_archived and archived:
                return Err(ProjectArchivedError())
            project.is_archived = archived
            await session.flush()
            output = ProjectArchiveResponse(
                project_id=str(project.uuid),
                archived=project.is_archived,
            )
            await session.commit()
            return Ok(output)
