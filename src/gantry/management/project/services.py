"""Business logic for project management."""

from gantry.keycloak import (
    KeycloakOrgError,
    OrgNotFoundError,
    MemberNotFoundError,
    KeycloakServiceClient,
    UserNotInOrganizationError,
)
from gantry.db.factories import AsyncSessionManager
from gantry.shared.utils.permission_utils import (
    normalize_project_permission_map,
    serialize_project_permission_map,
)
from gantry.management.organization.permissions import (
    OrgPermission,
    has_permission as has_org_permission,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .dtos import (
    ProjectInfoResponse,
    ProjectListResponse,
    ProjectUserResponse,
    ProjectArchiveResponse,
    ProjectSettingsResponse,
    ProjectUserListResponse,
    ProjectUserPermissionsResponse,
)
from .permissions import (
    PROJECT_PERMISSIONS_ATTR,
    ProjectPermission,
    has_permission,
)
from .repositories import (
    ProjectRepository,
    ProjectMemberRepository,
    ProjectSettingsRepository,
)

from typing import Any

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis
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
    """Coordinate project business rules across DB state and Keycloak attrs."""

    def __init__(
        self,
        session_manager: AsyncSessionManager,
        logger: BoundLogger,
        project_repo: ProjectRepository,
        membership_repo: ProjectMemberRepository,
        settings_repo: ProjectSettingsRepository,
        kc_client: KeycloakServiceClient,
        redis: Redis | None = None,
    ):
        self.session_manager = session_manager
        self.logger = logger
        self.project_repo = project_repo
        self.membership_repo = membership_repo
        self.settings_repo = settings_repo
        self.kc = kc_client
        self.redis = redis

    async def _ensureUserInOrg(
        self,
        user_id: str,
        org_id: str,
    ) -> Result[
        None,
        MemberNotFoundError | KeycloakOrgError | UserNotInOrganizationError,
    ]:
        """Verify that the user belongs to the owning organization."""
        orgs_res = await self.kc.getMemberOrganizations(user_id)
        if orgs_res.status == ResultStatus.Err:
            return orgs_res.into()
        for org in orgs_res.unwrap():
            if str(org.get("id", "")) == org_id:
                return Ok(None)
        return Err(UserNotInOrganizationError())

    async def _isProjectMember(
        self,
        project_id: int,
        user_id: str,
    ) -> bool:
        """Return whether the user is a direct member of the project."""
        async with self.session_manager.get_session() as session:
            membership = await self.membership_repo.getMembership(
                session, project_id, user_id
            )
            return membership is not None

    async def _getProjectOrErr(
        self, project_uuid: str
    ) -> Result[tuple[int, str, ProjectInfoResponse], ProjectNotFoundError]:
        """Load a project row and map it into the public DTO shape."""
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(session, project_uuid)
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

    def _ensureProjectActive(
        self,
        project_info: ProjectInfoResponse,
    ) -> Result[None, ProjectArchivedError]:
        """Reject operations that are not allowed on archived projects."""
        if project_info.archived:
            return Err(ProjectArchivedError())
        return Ok(None)

    def _flattenSettings(
        self,
        data: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Flatten nested project settings into dot-delimited keys."""
        flattened: dict[str, Any] = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flattened.update(self._flattenSettings(value, full_key))
            else:
                flattened[full_key] = value
        return flattened

    def _extractProjectPermissions(
        self,
        attrs: dict[str, Any],
        project_uuid: str,
    ) -> list[str]:
        """Extract project-scoped permissions from grouped Keycloak attrs."""
        grouped = normalize_project_permission_map(
            attrs.get(PROJECT_PERMISSIONS_ATTR, {})
        )
        return list(grouped.get(project_uuid, []))

    def _extractOrgPermissions(self, attrs: dict[str, Any]) -> list[str]:
        """Extract organization-scoped permissions from Keycloak attrs."""
        raw = attrs.get("org_permissions", [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            return [
                permission for permission in raw if isinstance(permission, str)
            ]
        return []

    async def _getOrgPermissions(
        self,
        org_id: str,
        user_id: str,
    ) -> Result[
        list[str],
        MemberNotFoundError | KeycloakOrgError | UserNotInOrganizationError,
    ]:
        """Load organization permissions for a confirmed org member."""
        in_org_res = await self._ensureUserInOrg(user_id, org_id)
        if in_org_res.status == ResultStatus.Err:
            return in_org_res.into()

        attrs_res = await self.kc.getUserAttributes(user_id)
        if attrs_res.status == ResultStatus.Err:
            return attrs_res.into()
        return Ok(self._extractOrgPermissions(attrs_res.unwrap()))

    async def _isOrgOwner(
        self,
        org_id: str,
        user_id: str,
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        """Return whether the actor is organization owner for the project org."""
        org_perms_res = await self._getOrgPermissions(org_id, user_id)
        if org_perms_res.status == ResultStatus.Err:
            if isinstance(
                org_perms_res.err(),
                UserNotInOrganizationError,
            ):
                return Ok(False)
            return org_perms_res.into()
        return Ok(
            has_org_permission(
                org_perms_res.unwrap(),
                OrgPermission.OWNER,
            )
        )

    async def _getPermissionsFromAttrs(
        self,
        user_id: str,
        project_uuid: str,
    ) -> Result[list[str], MemberNotFoundError | KeycloakOrgError]:
        """Load project permissions for one user directly from Keycloak attrs."""
        attrs_res = await self.kc.getUserAttributes(user_id)
        return attrs_res.map(
            lambda unwrapped: self._extractProjectPermissions(
                unwrapped, project_uuid
            )
        )

    async def _setProjectPermissions(
        self,
        user_id: str,
        project_uuid: str,
        permissions: list[str],
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        """Replace one project's permission slice inside the shared attr map."""
        attrs_res = await self.kc.getUserAttributes(user_id)
        if attrs_res.status == ResultStatus.Err:
            return attrs_res.into()

        attrs = attrs_res.unwrap()
        grouped = normalize_project_permission_map(
            attrs.get(PROJECT_PERMISSIONS_ATTR, {})
        )
        if permissions:
            grouped[project_uuid] = list(dict.fromkeys(permissions))
        else:
            grouped.pop(project_uuid, None)

        return await self.kc.setUserAttribute(
            user_id,
            PROJECT_PERMISSIONS_ATTR,
            serialize_project_permission_map(grouped),
        )

    async def _getMemberPermissions(
        self,
        project_id: int,
        project_uuid: str,
        user_id: str,
    ) -> Result[
        list[str],
        UserNotInProjectError | MemberNotFoundError | KeycloakOrgError,
    ]:
        """Return project permissions for a confirmed project member."""
        async with self.session_manager.get_session() as session:
            member = await self.membership_repo.getMembership(
                session, project_id, user_id
            )
            if member is None:
                return Err(UserNotInProjectError())
        return await self._getPermissionsFromAttrs(user_id, project_uuid)

    async def _countProjectOwners(
        self,
        project_id: int,
        project_uuid: str,
    ) -> Result[int, MemberNotFoundError | KeycloakOrgError]:
        """Count current owners by reading project-scoped attrs of all members."""
        async with self.session_manager.get_session() as session:
            members = await self.membership_repo.listMembers(
                session, project_id
            )
            member_user_ids = [member.user_id for member in members]

        owner_count = 0
        for member_user_id in member_user_ids:
            perms_res = await self._getPermissionsFromAttrs(
                member_user_id, project_uuid
            )
            if perms_res.status == ResultStatus.Err:
                return perms_res.into()
            if ProjectPermission.OWNER.value in perms_res.unwrap():
                owner_count += 1
        return Ok(owner_count)

    async def authorizeProjectPermission(
        self,
        project_uuid: str,
        user_id: str,
        required: ProjectPermission,
        allow_archived: bool = False,
    ) -> Result[
        None,
        ProjectNotFoundError
        | ProjectArchivedError
        | UserNotInProjectError
        | MemberNotFoundError
        | KeycloakOrgError
        | InsufficientProjectPermissionError,
    ]:
        """Authorize one project permission for the given user and project."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()
        if not allow_archived:
            active_res = self._ensureProjectActive(project_info)
            if active_res.status == ResultStatus.Err:
                return active_res
        org_owner_res = await self._isOrgOwner(org_id, user_id)
        if org_owner_res.status == ResultStatus.Err:
            return org_owner_res.into()
        if org_owner_res.unwrap():
            return Ok(None)
        perms_res = await self._getMemberPermissions(
            project_id, project_uuid, user_id
        )
        if perms_res.status == ResultStatus.Err:
            return perms_res.into()
        if not has_permission(perms_res.unwrap(), required):
            return Err(InsufficientProjectPermissionError())
        return Ok(None)

    async def listUserProjects(
        self,
        actor_user_id: str,
        organization_id: str | None = None,
    ) -> Result[
        ProjectListResponse,
        MemberNotFoundError | KeycloakOrgError | UserNotInOrganizationError,
    ]:
        """List projects joined by the actor, optionally within one org."""
        if organization_id:
            member_res = await self._ensureUserInOrg(
                actor_user_id, organization_id
            )
            if member_res.status == ResultStatus.Err:
                return member_res.into()

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.listByMember(
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

    async def listAccessibleProjects(
        self,
        actor_user_id: str,
        organization_id: str,
    ) -> Result[
        ProjectListResponse,
        MemberNotFoundError | KeycloakOrgError | UserNotInOrganizationError,
    ]:
        """List projects the actor can access in one organization."""
        org_owner_res = await self._isOrgOwner(
            organization_id,
            actor_user_id,
        )
        if org_owner_res.status == ResultStatus.Err:
            return org_owner_res.into()
        if org_owner_res.unwrap():
            async with self.session_manager.get_session() as session:
                projects = await self.project_repo.listByOrg(
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
        return await self.listUserProjects(actor_user_id, organization_id)

    async def _hasOrgWideProjectPermission(
        self,
        actor_user_id: str,
        organization_id: str,
        required: ProjectPermission,
    ) -> Result[bool, MemberNotFoundError | KeycloakOrgError]:
        """Check org-wide project permissions across all joined projects in an org."""
        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.listByMember(
                session, actor_user_id, organization_id=organization_id
            )
            project_uuids = [str(project.uuid) for project in projects]

        for project_uuid in project_uuids:
            perms_res = await self._getPermissionsFromAttrs(
                actor_user_id,
                project_uuid,
            )
            if perms_res.status == ResultStatus.Err:
                return perms_res.into()
            if has_permission(perms_res.unwrap(), required):
                return Ok(True)
        return Ok(False)

    async def listOrgProjects(
        self,
        actor_user_id: str,
        organization_id: str,
    ) -> Result[
        ProjectListResponse,
        MemberNotFoundError
        | KeycloakOrgError
        | InsufficientProjectPermissionError,
    ]:
        """List every project in an org when actor has org-wide project access."""
        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.listByOrg(
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

    async def createProject(
        self,
        actor_user_id: str,
        organization_id: str,
        name: str,
        description: str | None,
    ) -> Result[
        ProjectInfoResponse,
        MemberNotFoundError
        | KeycloakOrgError
        | UserNotInOrganizationError
        | InsufficientProjectPermissionError,
    ]:
        """Create a project and seed the creator as project owner."""
        org_perms_res = await self._getOrgPermissions(
            organization_id, actor_user_id
        )
        if org_perms_res.status == ResultStatus.Err:
            return org_perms_res.into()
        if not has_org_permission(
            org_perms_res.unwrap(),
            OrgPermission.PROJECTS_CREATE,
        ):
            return Err(InsufficientProjectPermissionError())

        async with self.session_manager.get_session() as session:
            project = await self.project_repo.create(
                session=session,
                name=name,
                description=description,
                organization_id=organization_id,
            )
            await self.membership_repo.upsertMembership(
                session=session,
                project_id=project.id,
                user_id=actor_user_id,
            )
            set_res = await self._setProjectPermissions(
                actor_user_id,
                str(project.uuid),
                [ProjectPermission.OWNER.value],
            )
            if set_res.status == ResultStatus.Err:
                return set_res.into()
            output = ProjectInfoResponse(
                id=str(project.uuid),
                name=project.name,
                description=project.description,
                organization_id=project.organization_id,
                archived=project.is_archived,
            )
            await session.commit()
            return Ok(output)

    async def getProject(
        self,
        project_uuid: str,
        actor_user_id: str,
    ) -> Result[
        ProjectInfoResponse,
        ProjectNotFoundError
        | MemberNotFoundError
        | KeycloakOrgError
        | UserNotInProjectError,
    ]:
        """Return one project if the actor can access it."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()

        org_owner_res = await self._isOrgOwner(org_id, actor_user_id)
        if org_owner_res.status == ResultStatus.Err:
            return org_owner_res.into()
        if org_owner_res.unwrap():
            return Ok(project_info)

        if await self._isProjectMember(project_id, actor_user_id):
            return Ok(project_info)

        return Err(UserNotInProjectError())

    async def updateProject(
        self,
        project_uuid: str,
        name: str,
        description: str | None,
    ) -> Result[
        ProjectInfoResponse,
        ProjectNotFoundError | ProjectArchivedError,
    ]:
        """Update mutable project metadata for one active project."""
        async with self.session_manager.get_session() as session:
            updated = await self.project_repo.updateByUuid(
                session,
                project_uuid,
                name=name,
                description=description,
            )
            if updated is None:
                return Err(ProjectNotFoundError())
            await session.commit()
            return Ok(
                ProjectInfoResponse(
                    id=str(updated.uuid),
                    name=updated.name,
                    description=updated.description,
                    organization_id=updated.organization_id,
                    archived=updated.is_archived,
                )
            )

    async def getProjectSettings(
        self,
        project_uuid: str,
    ) -> Result[
        ProjectSettingsResponse,
        ProjectNotFoundError,
    ]:
        """Fetch settings for one project, creating an empty row when missing."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, _ = project_res.unwrap()

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.getOrCreate(session, project_id)
            output = ProjectSettingsResponse(
                rate_limit=settings.rate_limit,
                spending_limit=settings.spending_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    async def updateProjectSettings(
        self,
        project_uuid: str,
        rate_limit: int | None,
        spending_limit: int | None,
        extra: dict[str, Any],
    ) -> Result[
        ProjectSettingsResponse,
        ProjectNotFoundError | ProjectArchivedError,
    ]:
        """Persist project settings and refresh the RPM cache."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()

        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        flattened_extra = self._flattenSettings(extra)

        async with self.session_manager.get_session() as session:
            settings = await self.settings_repo.upsert(
                session,
                project_id,
                rate_limit,
                spending_limit,
                flattened_extra,
            )
            output = ProjectSettingsResponse(
                rate_limit=settings.rate_limit,
                spending_limit=settings.spending_limit,
                extra=settings.extra or {},
            )
            await session.commit()
            return Ok(output)

    async def listProjectUsers(
        self,
        project_uuid: str,
        offset: int = 0,
        limit: int = 20,
        q: str | None = None,
    ) -> Result[
        ProjectUserListResponse,
        ProjectNotFoundError
        | ProjectArchivedError
        | OrgNotFoundError
        | KeycloakOrgError,
    ]:
        """List project members by intersecting project and org membership."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()
        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        async with self.session_manager.get_session() as session:
            members = await self.membership_repo.listMembers(
                session, project_id
            )
            user_ids = {m.user_id for m in members}

        users_res = await self.kc.getOrgMembers(
            org_id,
            first=0,
            max_results=1000,
            search=q,
        )
        if users_res.status == ResultStatus.Err:
            return users_res.into()
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

    async def addUserToProject(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[
        bool,
        ProjectNotFoundError
        | ProjectArchivedError
        | MemberNotFoundError
        | KeycloakOrgError
        | UserNotInOrganizationError
        | UserAlreadyInProjectError,
    ]:
        """Add an organization member to the project with empty project perms."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()
        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        in_org_res = await self._ensureUserInOrg(target_user_id, org_id)
        if in_org_res.status == ResultStatus.Err:
            return in_org_res.into()

        async with self.session_manager.get_session() as session:
            existing = await self.membership_repo.getMembership(
                session, project_id, target_user_id
            )
            if existing is not None:
                return Err(UserAlreadyInProjectError())
            await self.membership_repo.upsertMembership(
                session=session,
                project_id=project_id,
                user_id=target_user_id,
            )
            set_res = await self._setProjectPermissions(
                target_user_id,
                project_uuid,
                [ProjectPermission.MEMBER],
            )
            if set_res.status == ResultStatus.Err:
                return set_res
            await session.commit()
            return Ok(True)

    async def removeUserFromProject(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[
        bool,
        ProjectNotFoundError
        | ProjectArchivedError
        | UserNotInProjectError
        | MemberNotFoundError
        | KeycloakOrgError
        | LastOwnerRemovalNotAllowedError,
    ]:
        """Remove a project member while preserving the last-owner invariant."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, _, project_info = project_res.unwrap()
        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        async with self.session_manager.get_session() as session:
            membership = await self.membership_repo.getMembership(
                session, project_id, target_user_id
            )
            if membership is None:
                return Err(UserNotInProjectError())

            perms_res = await self._getPermissionsFromAttrs(
                target_user_id, project_uuid
            )
            if perms_res.status == ResultStatus.Err:
                return perms_res.into()
            if ProjectPermission.OWNER.value in perms_res.unwrap():
                owner_count_res = await self._countProjectOwners(
                    project_id, project_uuid
                )
                if owner_count_res.status == ResultStatus.Err:
                    return owner_count_res.into()
                if owner_count_res.unwrap() <= 1:
                    return Err(LastOwnerRemovalNotAllowedError())

            await self.membership_repo.deleteMembership(
                session, project_id, target_user_id
            )
            clear_res = await self._setProjectPermissions(
                target_user_id,
                project_uuid,
                [],
            )
            if clear_res.status == ResultStatus.Err:
                return clear_res
            await session.commit()
            return Ok(True)

    async def getUserPermissions(
        self,
        project_uuid: str,
        target_user_id: str,
    ) -> Result[
        ProjectUserPermissionsResponse,
        ProjectNotFoundError
        | ProjectArchivedError
        | UserNotInProjectError
        | MemberNotFoundError
        | KeycloakOrgError,
    ]:
        """Return project-scoped permissions for one project member."""
        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, _, project_info = project_res.unwrap()
        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        perms_res = await self._getMemberPermissions(
            project_id, project_uuid, target_user_id
        )
        if perms_res.status == ResultStatus.Err:
            return perms_res.into()

        return Ok(
            ProjectUserPermissionsResponse(permissions=perms_res.unwrap())
        )

    async def updateUserPermissions(
        self,
        project_uuid: str,
        actor_user_id: str,
        target_user_id: str,
        permissions: list[str],
    ) -> Result[
        ProjectUserPermissionsResponse,
        InvalidProjectPermissionError
        | ProjectNotFoundError
        | ProjectArchivedError
        | UserNotInProjectError
        | MemberNotFoundError
        | KeycloakOrgError
        | OwnerRequiredForGrantError
        | LastOwnerRemovalNotAllowedError,
    ]:
        """Replace one member's project permissions with owner safety checks."""
        valid = {p.value for p in ProjectPermission}
        invalid = set(permissions) - valid
        if invalid:
            return Err(InvalidProjectPermissionError())

        project_res = await self._getProjectOrErr(project_uuid)
        if project_res.status == ResultStatus.Err:
            return project_res.into()
        project_id, org_id, project_info = project_res.unwrap()
        active_res = self._ensureProjectActive(project_info)
        if active_res.status == ResultStatus.Err:
            return active_res.into()

        org_owner_res = await self._isOrgOwner(org_id, actor_user_id)
        if org_owner_res.status == ResultStatus.Err:
            return org_owner_res.into()
        if not org_owner_res.unwrap():
            actor_perms_res = await self._getMemberPermissions(
                project_id, project_uuid, actor_user_id
            )
            if actor_perms_res.status == ResultStatus.Err:
                return actor_perms_res.into()
            actor_perms = actor_perms_res.unwrap()

            if (
                ProjectPermission.USERS_PERMISSIONS_RW.value in permissions
                and not has_permission(actor_perms, ProjectPermission.OWNER)
            ):
                return Err(OwnerRequiredForGrantError())

        async with self.session_manager.get_session() as session:
            target = await self.membership_repo.getMembership(
                session, project_id, target_user_id
            )
            if target is None:
                return Err(UserNotInProjectError())

            target_perms_res = await self._getPermissionsFromAttrs(
                target_user_id, project_uuid
            )
            if target_perms_res.status == ResultStatus.Err:
                return target_perms_res.into()
            is_removing_owner = (
                ProjectPermission.OWNER.value in target_perms_res.unwrap()
                and ProjectPermission.OWNER.value not in permissions
            )
            if is_removing_owner:
                owner_count_res = await self._countProjectOwners(
                    project_id, project_uuid
                )
                if owner_count_res.status == ResultStatus.Err:
                    return owner_count_res.into()
                if owner_count_res.unwrap() <= 1:
                    return Err(LastOwnerRemovalNotAllowedError())

            set_res = await self._setProjectPermissions(
                target_user_id,
                project_uuid,
                permissions,
            )
            if set_res.status == ResultStatus.Err:
                return set_res.into()
            return Ok(ProjectUserPermissionsResponse(permissions=permissions))

    async def setProjectArchived(
        self,
        project_uuid: str,
        archived: bool,
    ) -> Result[
        ProjectArchiveResponse, ProjectNotFoundError | ProjectArchivedError
    ]:
        """Archive or unarchive a project after validating current state."""
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(session, project_uuid)
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
