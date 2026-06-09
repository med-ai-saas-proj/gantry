"""Admin-only orchestration service for dashboard routes."""

from gantry.db import AsyncSessionManager
from gantry.keycloak import (
    KeycloakOrgError,
    OrgNotFoundError,
    KeycloakServiceClient,
)
from gantry.management.api_key.dtos import (
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyWriteRequest,
    ApiKeyUpdateRequest,
    ApiKeyCreateResponse,
    ApiKeyPermissionCatalogResponse,
)
from gantry.management.project.dtos import (
    ProjectInfoResponse,
    ProjectListResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectArchiveResponse,
    ProjectSettingsResponse,
    ProjectUserListResponse,
    UpdateProjectSettingsRequest,
    ProjectPermissionCatalogResponse,
)
from gantry.management.auth.entities import AdminInfo
from gantry.management.api_key.services import (
    ApiKeyService,
    ApiKeyNotFoundError,
)
from gantry.management.project.services import (
    ProjectService,
    ProjectNotFoundError,
)
from gantry.management.organization.dtos import (
    OrgInfoResponse,
    OrgListResponse,
    CreateOrgRequest,
    OrgSettingsResponse,
    OrgUserListResponse,
    DeleteRequestResponse,
    UpdateSettingsRequest,
    UpdateOrgMetadataRequest,
    PermissionCatalogResponse,
)
from gantry.management.project.permissions import (
    ALL_PERMISSIONS as ALL_PROJECT_PERMISSIONS,
)
from gantry.management.api_key.repositories import ApiKeyRepository
from gantry.management.project.repositories import ProjectRepository
from gantry.management.organization.services import OrgService
from gantry.management.organization.permissions import (
    ALL_PERMISSIONS as ALL_ORG_PERMISSIONS,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .dtos import (
    AdminPaginationQuery,
    AdminUserInfoResponse,
    AdminUserListResponse,
    AdminUserProfileResponse,
    AdminUserListItemResponse,
    AdminDashboardSummaryResponse,
    AdminUserPermissionUpdateRequest,
    AdminUserOrganizationInfoResponse,
    AdminUserPermissionSummaryResponse,
    AdminUserProjectPermissionUpdateRequest,
)
from .permissions import (
    ORG_PERMISSIONS_ATTR,
    PROJECT_PERMISSIONS_ATTR,
    build_permission_summary,
    flatten_project_permission_updates,
)

from typing import Any


class InvalidAdminPermissionError(RecoverableError):
    """Raised when admin payload contains unknown org/project permissions."""

    status = 400
    code = "invalid_permission"
    title = "Invalid Permission"
    detail = "One or more permission strings are invalid."


class AdminService:
    """Coordinate admin-only routes across domain services and storage."""

    def __init__(
        self,
        session_manager: AsyncSessionManager,
        kc_org_client: KeycloakServiceClient,
        org_service: OrgService,
        project_service: ProjectService,
        apikey_service: ApiKeyService,
        project_repo: ProjectRepository,
        api_key_repo: ApiKeyRepository,
    ):
        self.session_manager = session_manager
        self.kc = kc_org_client
        self.org_service = org_service
        self.project_service = project_service
        self.apikey_service = apikey_service
        self.project_repo = project_repo
        self.api_key_repo = api_key_repo

    def _validatePermissionUpdatePayload(
        self,
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
            error = InvalidAdminPermissionError(
                message="Invalid organization permissions: "
                + ", ".join(invalid_org_permissions)
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
            error = InvalidAdminPermissionError(
                message="Invalid project permissions: "
                + ", ".join(invalid_project_permissions)
            )
            raise error

    @staticmethod
    def _raiseInvalidPermissions(
        scope: str,
        permissions: list[str],
        allowed_permissions: list[str],
    ) -> None:
        """Fail fast for one permission scope before loading user profile."""
        invalid_permissions = sorted(
            {
                permission
                for permission in permissions
                if permission not in allowed_permissions
            }
        )
        if invalid_permissions:
            error = InvalidAdminPermissionError(
                message=f"Invalid {scope} permissions: "
                + ", ".join(invalid_permissions)
            )
            raise error

    @staticmethod
    def _toProjectInfoResponse(project: Any) -> ProjectInfoResponse:
        """Map a project row to the public admin DTO."""
        return ProjectInfoResponse(
            project_uuid=str(project.uuid),
            name=project.name,
            description=project.description,
            organization_id=project.organization_id,
            archived=project.is_archived,
        )

    async def _getProjectInfoOrErr(
        self,
        project_id: str,
    ) -> ProjectInfoResponse:
        """Load one project row and map it before leaving the session."""
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(session, project_id)
            if project is None:
                raise ProjectNotFoundError()
            return self._toProjectInfoResponse(project)

    async def _buildUserProfileResponse(
        self,
        user_id: str,
    ) -> AdminUserProfileResponse:
        """Load one user's Keycloak profile and map it into the admin response."""
        profile_res = await self.kc.getUserProfile(user_id)
        profile = profile_res.unwrap()

        orgs_res = await self.kc.getMemberOrganizations(user_id)
        organizations = orgs_res.unwrap()

        attrs = profile.get("attributes", {})
        if not isinstance(attrs, dict):
            attrs = {}

        return AdminUserProfileResponse(
            user_id=str(profile["id"]),
            username=profile.get("username"),
            email=profile.get("email"),
            first_name=profile.get("firstName"),
            last_name=profile.get("lastName"),
            enabled=bool(profile.get("enabled", False)),
            email_verified=bool(profile.get("emailVerified", False)),
            organizations=[
                AdminUserOrganizationInfoResponse(
                    org_id=str(org["id"]),
                    name=org.get("name"),
                    alias=org.get("alias"),
                )
                for org in organizations
                if isinstance(org.get("id"), str)
            ],
            permissions=build_permission_summary(attrs),
        )

    def getAdminInfo(self, admin_info: AdminInfo) -> AdminUserInfoResponse:
        """Return the authenticated admin identity DTO."""
        return AdminUserInfoResponse(
            user_id=admin_info["id"],
            username=admin_info["username"],
            email=admin_info["email"],
        )

    async def getDashboardSummary(self) -> AdminDashboardSummaryResponse:
        """Return top-level counters for the admin dashboard home."""
        orgs_res = await self.org_service.listOrgs(limit=1000, offset=0, q=None)
        organizations = orgs_res.unwrap().total

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.countAll(session)
            api_keys = await self.api_key_repo.countAll(session)

        user_count_res = await self.kc.countUsers(search=None)
        users = user_count_res.unwrap_or(0)
        return AdminDashboardSummaryResponse(
            organizations=organizations,
            projects=projects,
            api_keys=api_keys,
            users=users,
        )

    def listOrganizationPermissions(self) -> PermissionCatalogResponse:
        """Return the organization permission catalog."""
        return PermissionCatalogResponse(permissions=ALL_ORG_PERMISSIONS)

    async def listOrganizations(
        self,
        pagination: AdminPaginationQuery,
    ) -> OrgListResponse:
        """Return organizations without requiring membership in each org."""
        result = await self.org_service.listOrgs(
            limit=pagination.limit,
            offset=pagination.offset,
            q=pagination.q,
        )
        return result.unwrap()

    async def createOrganization(
        self,
        input_data: CreateOrgRequest,
    ) -> OrgInfoResponse:
        """Create an organization and optionally seed an owner membership."""
        result = await self.org_service.createOrg(
            name=input_data.name,
            alias=input_data.alias,
            owner_id=input_data.owner_id,
        )
        return result.unwrap()

    async def getOrganization(self, org_id: str) -> OrgInfoResponse:
        """Return one organization without user-scope permission checks."""
        result = await self.org_service.getOrgInfo(org_id)
        return result.unwrap()

    async def getOrganizationSettings(
        self,
        org_id: str,
    ) -> OrgSettingsResponse:
        """Return organization settings without requiring org membership."""
        result = await self.org_service.getSettings(org_id)
        return result.unwrap()

    async def updateOrganizationSettings(
        self,
        org_id: str,
        input_data: UpdateSettingsRequest,
    ) -> OrgSettingsResponse:
        """Update organization settings without requiring org-owner permission."""
        result = await self.org_service.updateSettings(
            org_id,
            input_data.rate_limit,
            input_data.spending_limit,
            input_data.extra,
        )
        return result.unwrap()

    async def listOrganizationUsers(
        self,
        org_id: str,
        pagination: AdminPaginationQuery,
    ) -> OrgUserListResponse:
        """Return organization members for org detail screens."""
        result = await self.org_service.getUsers(
            org_id,
            limit=pagination.limit,
            offset=pagination.offset,
            q=pagination.q,
        )
        return result.unwrap()

    async def updateOrganization(
        self,
        org_id: str,
        input_data: UpdateOrgMetadataRequest,
    ) -> OrgInfoResponse:
        """Rename one organization without requiring org-owner membership."""
        current_org_res = await self.kc.getOrg(org_id)
        current_org = current_org_res.unwrap()
        payload = dict(current_org)
        payload["name"] = input_data.name

        update_res = await self.kc.updateOrg(org_id, payload)
        update_res.unwrap()

        return OrgInfoResponse(
            org_id=org_id,
            name=input_data.name,
            owner_id=None,
        )

    async def deleteOrganization(
        self,
        org_id: str,
    ) -> DeleteRequestResponse:
        """Request delayed organization deletion through the existing lifecycle."""
        result = await self.org_service.requestDeleteOrg(org_id)
        return result.unwrap()

    def listProjectPermissions(self) -> ProjectPermissionCatalogResponse:
        """Return the project permission catalog."""
        return ProjectPermissionCatalogResponse(
            permissions=ALL_PROJECT_PERMISSIONS
        )

    async def listProjects(
        self,
        org_id: str,
        pagination: AdminPaginationQuery,
    ) -> ProjectListResponse:
        """Return one page of projects in an organization for admin access."""
        org_res = await self.kc.getOrg(org_id)
        org_res.unwrap()

        async with self.session_manager.get_session() as session:
            projects = await self.project_repo.listByOrg(
                session,
                org_id,
                q=pagination.q,
            )
            paged_projects = projects[
                pagination.offset : pagination.offset + pagination.limit
            ]
            return ProjectListResponse(
                total=len(projects),
                results=[
                    self._toProjectInfoResponse(project)
                    for project in paged_projects
                ],
            )

    async def createProject(
        self,
        org_id: str,
        input_data: CreateProjectRequest,
    ) -> ProjectInfoResponse:
        """Create a project in an organization without user-scoped checks."""
        org_res = await self.kc.getOrg(org_id)
        org_res.unwrap()

        async with self.session_manager.get_session() as session:
            project = await self.project_repo.create(
                session=session,
                name=input_data.name,
                description=input_data.description,
                organization_id=org_id,
            )
            await session.commit()
            return self._toProjectInfoResponse(project)

    async def getProject(self, project_id: str) -> ProjectInfoResponse:
        """Return one project without requiring project membership."""
        return await self._getProjectInfoOrErr(project_id)

    async def getProjectSettings(
        self,
        project_id: str,
    ) -> ProjectSettingsResponse:
        """Return project settings without requiring project membership."""
        result = await self.project_service.getProjectSettings(project_id)
        return result.unwrap()

    async def updateProjectSettings(
        self,
        project_id: str,
        input_data: UpdateProjectSettingsRequest,
    ) -> ProjectSettingsResponse:
        """Update project settings without project permission checks."""
        result = await self.project_service.updateProjectSettings(
            project_id,
            input_data.rate_limit,
            input_data.spending_limit,
            input_data.extra,
        )
        return result.unwrap()

    async def listProjectUsers(
        self,
        project_id: str,
        pagination: AdminPaginationQuery,
    ) -> ProjectUserListResponse:
        """Return project members for project detail screens."""
        result = await self.project_service.listProjectUsers(
            project_id,
            offset=pagination.offset,
            limit=pagination.limit,
            q=pagination.q,
        )
        return result.unwrap()

    async def updateProject(
        self,
        project_id: str,
        input_data: UpdateProjectRequest,
    ) -> ProjectInfoResponse:
        """Update one project without project permission checks."""
        result = await self.project_service.updateProject(
            project_uuid=project_id,
            name=input_data.name,
            description=input_data.description,
        )
        return result.unwrap()

    async def deleteProject(
        self,
        project_id: str,
    ) -> ProjectArchiveResponse:
        """Soft-delete one project by marking it archived."""
        return await self.archiveProject(project_id)

    async def archiveProject(
        self,
        project_id: str,
    ) -> ProjectArchiveResponse:
        """Archive one project without project permission checks."""
        result = await self.project_service.setProjectArchived(
            project_uuid=project_id,
            archived=True,
        )
        return result.unwrap()

    async def unarchiveProject(
        self,
        project_id: str,
    ) -> ProjectArchiveResponse:
        """Unarchive one project without project permission checks."""
        result = await self.project_service.setProjectArchived(
            project_uuid=project_id,
            archived=False,
        )
        return result.unwrap()

    def listApiKeyPermissions(self) -> ApiKeyPermissionCatalogResponse:
        """Return the API-key permission catalog."""
        return self.apikey_service.getPermissionCatalog()

    async def listApiKeys(
        self, project_id: str, disabled: bool | None = None
    ) -> ApiKeyListResponse:
        """Return API keys for one project without permission checks."""
        result = await self.apikey_service.getApiKeys(
            project_uuid=project_id,
            disabled=disabled,
        )
        return result.unwrap()

    async def createApiKey(
        self,
        admin_info: AdminInfo,
        project_id: str,
        input_data: ApiKeyWriteRequest,
    ) -> ApiKeyCreateResponse:
        """Create an API key in one project without project permission checks."""
        result = await self.apikey_service.createApiKey(
            actor_user_id=admin_info["id"],
            project_uuid=project_id,
            name=input_data.name,
            description=input_data.description,
            permissions=input_data.permissions,
        )
        return result.unwrap()

    async def getApiKey(
        self,
        api_key_uuid: str,
        disabled: bool | None = None,
    ) -> ApiKeyResponse:
        """Return one API key without project permission checks."""
        result = await self.apikey_service.getApiKey(api_key_uuid)
        api_key = result.unwrap()
        if disabled is not None and api_key.disabled != disabled:
            raise ApiKeyNotFoundError()
        return api_key

    async def updateApiKey(
        self,
        api_key_uuid: str,
        input_data: ApiKeyUpdateRequest,
    ) -> ApiKeyResponse:
        """Update one API key without project permission checks."""
        result = await self.apikey_service.updateApiKey(
            api_key_uuid=api_key_uuid,
            name=input_data.name,
            description=input_data.description,
            permissions=input_data.permissions,
            disabled=input_data.disabled,
        )
        return result.unwrap()

    async def deleteApiKey(self, api_key_uuid: str) -> bool:
        """Delete one API key without project permission checks."""
        result = await self.apikey_service.deleteApiKey(api_key_uuid)
        result.unwrap()
        return True

    async def listUsers(
        self,
        pagination: AdminPaginationQuery,
    ) -> AdminUserListResponse:
        """List Keycloak users with pagination and optional search."""
        users_res = await self.kc.listUsers(
            first=pagination.offset,
            max_results=pagination.limit,
            search=pagination.q,
        )
        users = users_res.unwrap()
        count_res = await self.kc.countUsers(search=pagination.q)
        total = count_res.unwrap_or(len(users))
        return AdminUserListResponse(
            total=total,
            results=[
                AdminUserListItemResponse(
                    user_id=str(user.get("id") or ""),
                    username=user.get("username"),
                    email=user.get("email"),
                    first_name=user.get("firstName"),
                    last_name=user.get("lastName"),
                    enabled=bool(user.get("enabled", False)),
                    email_verified=bool(user.get("emailVerified", False)),
                )
                for user in users
                if user.get("id")
            ],
        )

    async def getUserOrganizations(
        self,
        user_id: str,
    ) -> list[AdminUserOrganizationInfoResponse]:
        """Return organization memberships for any user after admin auth."""
        result = await self.kc.getMemberOrganizations(user_id)
        organizations = result.unwrap()
        return [
            AdminUserOrganizationInfoResponse(
                org_id=str(org["id"]),
                name=org.get("name"),
                alias=org.get("alias"),
            )
            for org in organizations
            if isinstance(org.get("id"), str)
        ]

    async def getUserProfile(self, user_id: str) -> AdminUserProfileResponse:
        """Return one user's Keycloak profile and permission data."""
        return await self._buildUserProfileResponse(user_id)

    async def getUserPermissions(
        self,
        user_id: str,
    ) -> AdminUserPermissionSummaryResponse:
        """Return only one user's normalized permission summary."""
        profile = await self._buildUserProfileResponse(user_id)
        return profile.permissions

    @staticmethod
    def _projectPermissionUpdatesFromSummary(
        summary: AdminUserPermissionSummaryResponse,
    ) -> list[AdminUserProjectPermissionUpdateRequest]:
        """Convert profile summary back into the write DTO shape."""
        return [
            AdminUserProjectPermissionUpdateRequest(
                project_uuid=item.project_uuid,
                permissions=item.permissions,
            )
            for item in summary.project_permissions
        ]

    async def setUserOrganizationPermissions(
        self,
        user_id: str,
        org_id: str,
        permissions: list[str],
    ) -> AdminUserProfileResponse:
        """Replace organization permissions while preserving project permissions."""
        del org_id
        self._raiseInvalidPermissions(
            "organization",
            permissions,
            ALL_ORG_PERMISSIONS,
        )
        profile = await self._buildUserProfileResponse(user_id)
        payload = AdminUserPermissionUpdateRequest(
            organization_permissions=permissions,
            project_permissions=self._projectPermissionUpdatesFromSummary(
                profile.permissions
            ),
        )
        return await self.setUserPermissions(user_id, payload)

    async def setUserProjectPermissions(
        self,
        user_id: str,
        project_id: str,
        permissions: list[str],
    ) -> AdminUserProfileResponse:
        """Replace one project's permissions while preserving every other scope."""
        self._raiseInvalidPermissions(
            "project",
            permissions,
            ALL_PROJECT_PERMISSIONS,
        )
        profile = await self._buildUserProfileResponse(user_id)
        project_permissions = [
            item
            for item in self._projectPermissionUpdatesFromSummary(
                profile.permissions
            )
            if item.project_uuid != project_id
        ]
        project_permissions.append(
            AdminUserProjectPermissionUpdateRequest(
                project_uuid=project_id,
                permissions=permissions,
            )
        )
        payload = AdminUserPermissionUpdateRequest(
            organization_permissions=profile.permissions.organization_permissions,
            project_permissions=project_permissions,
        )
        return await self.setUserPermissions(user_id, payload)

    async def setUserPermissions(
        self,
        user_id: str,
        payload: AdminUserPermissionUpdateRequest,
    ) -> AdminUserProfileResponse:
        """Replace one user's permission attributes through Keycloak admin API."""
        self._validatePermissionUpdatePayload(payload)
        update_res = await self.kc.setUserAttributes(
            user_id,
            {
                ORG_PERMISSIONS_ATTR: payload.organization_permissions,
                PROJECT_PERMISSIONS_ATTR: flatten_project_permission_updates(
                    payload.project_permissions
                ),
            },
        )
        update_res.unwrap()
        return await self._buildUserProfileResponse(user_id)

    async def resetUserPermissions(
        self,
        user_id: str,
    ) -> AdminUserProfileResponse:
        """Clear one user's org/project permission attributes in Keycloak."""
        update_res = await self.kc.setUserAttributes(
            user_id,
            {
                ORG_PERMISSIONS_ATTR: [],
                PROJECT_PERMISSIONS_ATTR: {},
            },
        )
        update_res.unwrap()
        return await self._buildUserProfileResponse(user_id)
