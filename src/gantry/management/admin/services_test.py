from gantry.management.admin.dtos import (
    AdminPaginationQuery,
    AdminUserPermissionUpdateRequest,
    AdminUserProjectPermissionUpdateRequest,
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
    ProjectUserResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectArchiveResponse,
    ProjectSettingsResponse,
    ProjectUserListResponse,
    UpdateProjectSettingsRequest,
)
from gantry.management.admin.services import (
    AdminService,
    InvalidAdminPermissionError,
)
from gantry.management.project.services import ProjectNotFoundError
from gantry.management.organization.dtos import (
    OrgInfoResponse,
    OrgListResponse,
    OrgUserResponse,
    CreateOrgRequest,
    OrgSettingsResponse,
    OrgUserListResponse,
    DeleteRequestResponse,
    UpdateSettingsRequest,
    UpdateOrgMetadataRequest,
    PermissionCatalogResponse,
)

import unittest
from types import SimpleNamespace
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock, call

from pyrusult import Ok


class _DummySessionManager:
    def __init__(self):
        self.session = Mock()
        self.session.commit = AsyncMock()

    @asynccontextmanager
    async def get_session(self):
        yield self.session


class TestAdminService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session_manager = _DummySessionManager()
        self.kc = Mock()
        self.org_service = Mock()
        self.project_service = Mock()
        self.apikey_service = Mock()
        self.project_repo = Mock()
        self.api_key_repo = Mock()
        self.service = AdminService(
            session_manager=self.session_manager,
            kc_org_client=self.kc,
            org_service=self.org_service,
            project_service=self.project_service,
            apikey_service=self.apikey_service,
            project_repo=self.project_repo,
            api_key_repo=self.api_key_repo,
        )
        self.user_info = {
            "id": "admin-1",
            "username": "admin",
            "email": "admin@test",
        }

    def test_get_admin_info_maps_identity(self):
        result = self.service.getAdminInfo(self.user_info)

        self.assertEqual(result.user_id, "admin-1")
        self.assertEqual(result.username, "admin")

    def test_list_organization_permissions_returns_catalog(self):
        result = self.service.listOrganizationPermissions()

        self.assertIsInstance(result, PermissionCatalogResponse)
        self.assertIn("organization.owner", result.permissions)

    async def test_list_organizations_delegates_to_org_service(self):
        pagination = AdminPaginationQuery(limit=10, offset=5, q="org")
        expected = OrgListResponse(
            total=1,
            results=[
                OrgInfoResponse(org_id="org-1", name="Org 1", owner_id=None)
            ],
        )
        self.org_service.listOrgs = AsyncMock(return_value=Ok(expected))

        result = await self.service.listOrganizations(pagination)

        self.assertEqual(result, expected)
        self.org_service.listOrgs.assert_awaited_once_with(
            limit=10,
            offset=5,
            q="org",
        )

    async def test_create_organization_delegates_to_org_service(self):
        request = CreateOrgRequest(
            name="Org 1",
            alias="org-1",
            owner_id="user-1",
        )
        expected = OrgInfoResponse(
            org_id="org-1",
            name="Org 1",
            owner_id="user-1",
        )
        self.org_service.createOrg = AsyncMock(return_value=Ok(expected))

        result = await self.service.createOrganization(request)

        self.assertEqual(result, expected)
        self.org_service.createOrg.assert_awaited_once_with(
            name="Org 1",
            alias="org-1",
            owner_id="user-1",
        )

    async def test_get_organization_delegates_to_org_service(self):
        expected = OrgInfoResponse(
            org_id="org-1",
            name="Org 1",
            owner_id=None,
        )
        self.org_service.getOrgInfo = AsyncMock(return_value=Ok(expected))

        result = await self.service.getOrganization("org-1")

        self.assertEqual(result, expected)
        self.org_service.getOrgInfo.assert_awaited_once_with("org-1")

    async def test_get_and_update_organization_settings_delegate(self):
        current = OrgSettingsResponse(
            rate_limit=100,
            spending_limit=5000,
            extra={"env": "dev"},
        )
        updated = OrgSettingsResponse(
            rate_limit=120,
            spending_limit=7000,
            extra={"env": "prod"},
        )
        self.org_service.getSettings = AsyncMock(return_value=Ok(current))
        self.org_service.updateSettings = AsyncMock(return_value=Ok(updated))

        get_result = await self.service.getOrganizationSettings("org-1")
        update_result = await self.service.updateOrganizationSettings(
            "org-1",
            UpdateSettingsRequest(
                rate_limit=120,
                spending_limit=7000,
                extra={"env": "prod"},
            ),
        )

        self.assertEqual(get_result, current)
        self.assertEqual(update_result, updated)
        self.org_service.getSettings.assert_awaited_once_with("org-1")
        self.org_service.updateSettings.assert_awaited_once_with(
            "org-1",
            120,
            7000,
            {"env": "prod"},
        )

    async def test_list_organization_users_and_delete_delegate(self):
        pagination = AdminPaginationQuery(limit=10, offset=0, q="alice")
        users = OrgUserListResponse(
            total=1,
            results=[
                OrgUserResponse(
                    id="user-1",
                    username="alice",
                    email="alice@test",
                )
            ],
        )
        deletion = DeleteRequestResponse(
            id="org-1",
            requested_at="2026-05-02T00:00:00+00:00",
            cancel_before="2026-06-01T00:00:00+00:00",
        )
        self.org_service.getUsers = AsyncMock(return_value=Ok(users))
        self.org_service.requestDeleteOrg = AsyncMock(return_value=Ok(deletion))

        users_result = await self.service.listOrganizationUsers(
            "org-1",
            pagination,
        )
        delete_result = await self.service.deleteOrganization("org-1")

        self.assertEqual(users_result, users)
        self.assertEqual(delete_result, deletion)
        self.org_service.getUsers.assert_awaited_once_with(
            "org-1",
            limit=10,
            offset=0,
            q="alice",
        )
        self.org_service.requestDeleteOrg.assert_awaited_once_with("org-1")

    def test_list_project_permissions_returns_catalog(self):
        result = self.service.listProjectPermissions()

        self.assertIn("project.owner", result.permissions)

    async def test_get_dashboard_summary_aggregates_counts(self):
        self.org_service.listOrgs = AsyncMock(
            return_value=Ok(SimpleNamespace(total=3, results=[]))
        )
        self.project_repo.countAll = AsyncMock(return_value=5)
        self.api_key_repo.countAll = AsyncMock(return_value=8)
        self.kc.countUsers = AsyncMock(return_value=Ok(13))

        result = await self.service.getDashboardSummary()

        self.assertEqual(result.organizations, 3)
        self.assertEqual(result.projects, 5)
        self.assertEqual(result.api_keys, 8)
        self.assertEqual(result.users, 13)
        self.org_service.listOrgs.assert_awaited_once_with(
            limit=1000,
            offset=0,
            q=None,
        )
        self.project_repo.countAll.assert_awaited_once_with(
            self.session_manager.session
        )
        self.api_key_repo.countAll.assert_awaited_once_with(
            self.session_manager.session
        )
        self.kc.countUsers.assert_awaited_once_with(search=None)

    async def test_update_organization_uses_keycloak_payload_round_trip(self):
        self.kc.getOrg = AsyncMock(
            return_value=Ok({"id": "org-1", "name": "Old", "alias": "old"})
        )
        self.kc.updateOrg = AsyncMock(return_value=Ok(True))

        result = await self.service.updateOrganization(
            "org-1",
            UpdateOrgMetadataRequest(name="New Org"),
        )

        self.assertEqual(result.org_id, "org-1")
        self.assertEqual(result.name, "New Org")
        self.kc.updateOrg.assert_awaited_once_with(
            "org-1",
            {"id": "org-1", "name": "New Org", "alias": "old"},
        )

    async def test_list_projects_checks_org_and_maps_rows(self):
        self.kc.getOrg = AsyncMock(return_value=Ok({"id": "org-1"}))
        self.project_repo.listByOrg = AsyncMock(
            return_value=[
                SimpleNamespace(
                    uuid="project-1",
                    name="Project 1",
                    description="desc",
                    organization_id="org-1",
                    is_archived=False,
                )
            ]
        )

        result = await self.service.listProjects("org-1")

        self.assertEqual(result.total, 1)
        self.assertEqual(result.results[0].project_uuid, "project-1")
        self.project_repo.listByOrg.assert_awaited_once_with(
            self.session_manager.session,
            "org-1",
        )

    async def test_create_project_commits_and_maps_row(self):
        self.kc.getOrg = AsyncMock(return_value=Ok({"id": "org-1"}))
        self.project_repo.create = AsyncMock(
            return_value=SimpleNamespace(
                uuid="project-1",
                name="Project 1",
                description="desc",
                organization_id="org-1",
                is_archived=False,
            )
        )

        result = await self.service.createProject(
            "org-1",
            CreateProjectRequest(name="Project 1", description="desc"),
        )

        self.assertEqual(result.project_uuid, "project-1")
        self.session_manager.session.commit.assert_awaited_once()
        self.project_repo.create.assert_awaited_once_with(
            session=self.session_manager.session,
            name="Project 1",
            description="desc",
            organization_id="org-1",
        )

    async def test_get_project_raises_when_project_missing(self):
        self.project_repo.getByUuid = AsyncMock(return_value=None)

        with self.assertRaises(ProjectNotFoundError):
            await self.service.getProject("missing-project")

    async def test_user_profile_builds_permission_summary(self):
        self.kc.getUserProfile = AsyncMock(
            return_value=Ok(
                {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@test",
                    "firstName": "Alice",
                    "lastName": "Nguyen",
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {
                        "org_permissions": ["organization.owner"],
                        "project_permissions": {
                            "project-a": [
                                "project.owner",
                                "project.settings.read",
                            ],
                            "project-b": ["apikey.read"],
                        },
                    },
                }
            )
        )
        self.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [{"id": "org-1", "name": "Org 1", "alias": "org-1"}]
            )
        )

        result = await self.service.getUserProfile("user-1")

        self.assertEqual(result.user_id, "user-1")
        self.assertEqual(len(result.organizations), 1)
        self.assertEqual(
            result.permissions.organization_permissions,
            ["organization.owner"],
        )
        self.assertEqual(len(result.permissions.project_permissions), 2)
        self.assertEqual(
            result.permissions.project_permissions[0].project_uuid,
            "project-a",
        )

    async def test_get_update_project_settings_and_users_delegate(self):
        pagination = AdminPaginationQuery(limit=10, offset=5, q="alice")
        current = ProjectSettingsResponse(
            rate_limit=40,
            spending_limit=9000,
            extra={"tier": "a"},
        )
        updated = ProjectSettingsResponse(
            rate_limit=55,
            spending_limit=9900,
            extra={"tier": "b"},
        )
        users = ProjectUserListResponse(
            total=1,
            results=[
                ProjectUserResponse(
                    id="user-1",
                    username="alice",
                    email="alice@test",
                )
            ],
        )
        self.project_service.getProjectSettings = AsyncMock(
            return_value=Ok(current)
        )
        self.project_service.updateProjectSettings = AsyncMock(
            return_value=Ok(updated)
        )
        self.project_service.listProjectUsers = AsyncMock(
            return_value=Ok(users)
        )

        get_result = await self.service.getProjectSettings("project-1")
        update_result = await self.service.updateProjectSettings(
            "project-1",
            UpdateProjectSettingsRequest(
                rate_limit=55,
                spending_limit=9900,
                extra={"tier": "b"},
            ),
        )
        users_result = await self.service.listProjectUsers(
            "project-1",
            pagination,
        )

        self.assertEqual(get_result, current)
        self.assertEqual(update_result, updated)
        self.assertEqual(users_result, users)
        self.project_service.getProjectSettings.assert_awaited_once_with(
            "project-1"
        )
        self.project_service.updateProjectSettings.assert_awaited_once_with(
            "project-1",
            55,
            9900,
            {"tier": "b"},
        )
        self.project_service.listProjectUsers.assert_awaited_once_with(
            "project-1",
            offset=5,
            limit=10,
            q="alice",
        )

    async def test_update_archive_unarchive_and_delete_project_delegate(self):
        updated = ProjectInfoResponse(
            project_uuid="project-1",
            name="Renamed Project",
            description=None,
            organization_id="org-1",
            archived=False,
        )
        archived = ProjectArchiveResponse(
            id="project-1",
            archived=True,
        )
        unarchived = ProjectArchiveResponse(
            id="project-1",
            archived=False,
        )
        self.project_service.updateProject = AsyncMock(return_value=Ok(updated))
        self.project_service.setProjectArchived = AsyncMock(
            side_effect=[Ok(archived), Ok(unarchived), Ok(archived)]
        )

        update_result = await self.service.updateProject(
            "project-1",
            UpdateProjectRequest(
                name="Renamed Project",
                description=None,
            ),
        )
        archive_result = await self.service.archiveProject("project-1")
        unarchive_result = await self.service.unarchiveProject("project-1")
        delete_result = await self.service.deleteProject("project-1")

        self.assertEqual(update_result, updated)
        self.assertEqual(archive_result, archived)
        self.assertEqual(unarchive_result, unarchived)
        self.assertEqual(delete_result, archived)
        self.project_service.updateProject.assert_awaited_once_with(
            project_uuid="project-1",
            name="Renamed Project",
            description=None,
        )
        self.project_service.setProjectArchived.assert_has_awaits(
            [
                call(project_uuid="project-1", archived=True),
                call(project_uuid="project-1", archived=False),
                call(project_uuid="project-1", archived=True),
            ]
        )

    def test_list_api_key_permissions_returns_catalog(self):
        expected = ApiKeyPermissionCatalogResponse(
            total=2,
            results=[
                {"id": "apikey.read", "name": "apikey.read", "description": ""},
                {
                    "id": "apikey.write",
                    "name": "apikey.write",
                    "description": "",
                },
            ],
        )
        self.apikey_service.getPermissionCatalog = Mock(return_value=expected)

        result = self.service.listApiKeyPermissions()

        self.assertEqual(result, expected)
        self.apikey_service.getPermissionCatalog.assert_called_once_with()

    async def test_list_get_update_delete_api_keys_delegate(self):
        now = datetime.now(UTC)
        key = ApiKeyResponse(
            api_key_id=11,
            api_key_uuid="api-key-1",
            project_id=7,
            project_uuid="project-1",
            name="Key",
            description="desc",
            hint="sk_x...abcd",
            created_at=now,
            permissions=["objects:read"],
            disabled=False,
        )
        keys = ApiKeyListResponse(total=1, results=[key])
        updated = ApiKeyResponse(
            api_key_id=11,
            api_key_uuid="api-key-1",
            project_id=7,
            project_uuid="project-1",
            name="Renamed Key",
            description="",
            hint="sk_x...abcd",
            created_at=now,
            permissions=["objects:write"],
            disabled=False,
        )
        self.apikey_service.getApiKeys = AsyncMock(return_value=Ok(keys))
        self.apikey_service.getApiKey = AsyncMock(return_value=Ok(key))
        self.apikey_service.updateApiKey = AsyncMock(return_value=Ok(updated))
        self.apikey_service.deleteApiKey = AsyncMock(return_value=Ok(True))

        list_result = await self.service.listApiKeys(
            "project-1",
            disabled=True,
        )
        get_result = await self.service.getApiKey("api-key-1")
        update_result = await self.service.updateApiKey(
            "api-key-1",
            ApiKeyUpdateRequest(
                name="Renamed Key",
                description="",
                permissions=["objects:write"],
                disabled=True,
            ),
        )
        delete_result = await self.service.deleteApiKey("api-key-1")

        self.assertEqual(list_result, keys)
        self.assertEqual(get_result, key)
        self.assertEqual(update_result, updated)
        self.assertTrue(delete_result)
        self.apikey_service.getApiKeys.assert_awaited_once_with(
            project_uuid="project-1",
            disabled=True,
        )
        self.apikey_service.getApiKey.assert_awaited_once_with("api-key-1")
        self.apikey_service.updateApiKey.assert_awaited_once_with(
            api_key_uuid="api-key-1",
            name="Renamed Key",
            description="",
            permissions=["objects:write"],
            disabled=True,
        )
        self.apikey_service.deleteApiKey.assert_awaited_once_with("api-key-1")

    async def test_create_api_key_passes_actor_identity(self):
        now = datetime.now(UTC)
        expected = ApiKeyCreateResponse(
            api_key_id=11,
            api_key_uuid="api-key-1",
            project_id=7,
            project_uuid="project-1",
            name="Key",
            description="",
            hint="sk_x...abcd",
            created_at=now,
            permissions=["objects:read"],
            disabled=False,
            key="sk_raw.secret",
        )
        self.apikey_service.createApiKey = AsyncMock(return_value=Ok(expected))

        result = await self.service.createApiKey(
            self.user_info,
            "project-1",
            ApiKeyWriteRequest(
                name="Key",
                description="",
                permissions=["objects:read"],
            ),
        )

        self.assertEqual(result, expected)
        self.apikey_service.createApiKey.assert_awaited_once_with(
            actor_user_id="admin-1",
            project_uuid="project-1",
            name="Key",
            description="",
            permissions=["objects:read"],
        )

    async def test_set_user_permissions_updates_keycloak_and_returns_profile(
        self,
    ):
        payload = AdminUserPermissionUpdateRequest(
            organization_permissions=["organization.settings.read"],
            project_permissions=[
                AdminUserProjectPermissionUpdateRequest(
                    project_uuid="project-a",
                    permissions=["project.settings.read"],
                )
            ],
        )
        self.kc.setUserAttributes = AsyncMock(return_value=Ok(True))
        self.kc.getUserProfile = AsyncMock(
            return_value=Ok(
                {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@test",
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {
                        "org_permissions": ["organization.settings.read"],
                        "project_permissions": {
                            "project-a": ["project.settings.read"]
                        },
                    },
                }
            )
        )
        self.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))

        result = await self.service.setUserPermissions("user-1", payload)

        self.assertEqual(result.user_id, "user-1")
        self.kc.setUserAttributes.assert_awaited_once_with(
            "user-1",
            {
                "org_permissions": ["organization.settings.read"],
                "project_permissions": {"project-a": ["project.settings.read"]},
            },
        )

    async def test_get_user_permissions_returns_only_permission_summary(self):
        self.kc.getUserProfile = AsyncMock(
            return_value=Ok(
                {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@test",
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {
                        "org_permissions": ["organization.settings.read"],
                        "project_permissions": {
                            "project-a": ["project.settings.read"]
                        },
                    },
                }
            )
        )
        self.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))

        result = await self.service.getUserPermissions("user-1")

        self.assertEqual(
            result.organization_permissions,
            ["organization.settings.read"],
        )
        self.assertEqual(
            result.project_permissions[0].project_uuid, "project-a"
        )
        self.kc.getUserProfile.assert_awaited_once_with("user-1")

    async def test_reset_user_permissions_clears_keycloak_attributes(self):
        self.kc.setUserAttributes = AsyncMock(return_value=Ok(True))
        self.kc.getUserProfile = AsyncMock(
            return_value=Ok(
                {
                    "id": "user-1",
                    "username": "alice",
                    "email": "alice@test",
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {},
                }
            )
        )
        self.kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))

        result = await self.service.resetUserPermissions("user-1")

        self.assertEqual(result.permissions.organization_permissions, [])
        self.kc.setUserAttributes.assert_awaited_once_with(
            "user-1",
            {
                "org_permissions": [],
                "project_permissions": {},
            },
        )

    async def test_set_user_permissions_rejects_invalid_org_permission(self):
        payload = AdminUserPermissionUpdateRequest(
            organization_permissions=["organization.nope"],
            project_permissions=[],
        )

        with self.assertRaises(InvalidAdminPermissionError):
            await self.service.setUserPermissions("user-1", payload)

    async def test_set_user_permissions_rejects_invalid_project_permission(
        self,
    ):
        payload = AdminUserPermissionUpdateRequest(
            organization_permissions=[],
            project_permissions=[
                AdminUserProjectPermissionUpdateRequest(
                    project_uuid="project-a",
                    permissions=["project.nope"],
                )
            ],
        )

        with self.assertRaises(InvalidAdminPermissionError):
            await self.service.setUserPermissions("user-1", payload)

    async def test_list_users_maps_keycloak_page(self):
        self.kc.listUsers = AsyncMock(
            return_value=Ok(
                [
                    {
                        "id": "user-1",
                        "username": "alice",
                        "email": "alice@test",
                        "firstName": "Alice",
                        "lastName": "Nguyen",
                        "enabled": True,
                        "emailVerified": True,
                    }
                ]
            )
        )
        self.kc.countUsers = AsyncMock(return_value=Ok(1))

        result = await self.service.listUsers(
            AdminPaginationQuery(limit=20, offset=0, q="alice")
        )

        self.assertEqual(result.total, 1)
        self.assertEqual(result.results[0].username, "alice")
        self.kc.listUsers.assert_awaited_once_with(
            first=0,
            max_results=20,
            search="alice",
        )
        self.kc.countUsers.assert_awaited_once_with(search="alice")

    async def test_get_user_organizations_maps_memberships(self):
        self.kc.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [
                    {"id": "org-1", "name": "Org 1", "alias": "org-1"},
                    {"id": "org-2", "name": "Org 2"},
                ]
            )
        )

        result = await self.service.getUserOrganizations("user-1")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].org_id, "org-1")
        self.kc.getMemberOrganizations.assert_awaited_once_with("user-1")
