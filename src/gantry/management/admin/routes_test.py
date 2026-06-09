from gantry.management.admin import routes

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock, AsyncMock

from fastapi import FastAPI


ADMIN_INFO = {
    "id": "admin-1",
    "username": "admin",
    "email": "admin@test",
}


class TestAdminRoutes(unittest.IsolatedAsyncioTestCase):
    def test_admin_openapi_uses_canonical_two_module_paths(self):
        app = FastAPI()
        app.include_router(routes.admin_router)

        paths = app.openapi()["paths"]

        self.assertIn("/admin/organizations/permissions", paths)
        self.assertIn("/admin/projects/permissions", paths)
        self.assertIn("/admin/api-keys/permissions", paths)
        self.assertIn("/admin/organizations/{org_id}/settings", paths)
        self.assertIn("/admin/organizations/{org_id}/users", paths)
        self.assertIn(
            "/admin/organizations/{org_id}/users/{user_id}/permissions",
            paths,
        )
        self.assertIn("/admin/projects/{project_id}/settings", paths)
        self.assertIn("/admin/projects/{project_id}/users", paths)
        self.assertIn(
            "/admin/projects/{project_id}/users/{user_id}/permissions",
            paths,
        )
        self.assertIn("/admin/users/{user_id}/organizations", paths)
        self.assertIn("/admin/users/{user_id}/profile", paths)
        self.assertIn("/admin/users/{user_id}/permissions", paths)

        self.assertNotIn("/admin/organization-permissions", paths)
        self.assertNotIn("/admin/project-permissions", paths)
        self.assertNotIn("/admin/api-key-permissions", paths)
        self.assertNotIn("/admin/organization-settings/{org_id}", paths)
        self.assertNotIn("/admin/organization-users", paths)
        self.assertNotIn("/admin/project-settings/{project_id}", paths)
        self.assertNotIn("/admin/project-users", paths)
        self.assertNotIn("/admin/user-organizations", paths)
        self.assertNotIn("/admin/user-profiles/{user_id}", paths)
        self.assertNotIn("/admin/user-permissions/{user_id}", paths)

    async def test_get_admin_me_delegates_to_admin_service(self):
        admin_service = Mock()
        expected = routes.AdminUserInfoResponse(
            user_id="admin-1",
            username="admin",
            email="admin@test",
        )
        admin_service.getAdminInfo.return_value = expected

        result = await routes.get_admin_me(ADMIN_INFO, admin_service)

        self.assertEqual(result, expected)
        admin_service.getAdminInfo.assert_called_once_with(ADMIN_INFO)

    async def test_get_admin_dashboard_summary_delegates_to_admin_service(self):
        admin_service = Mock()
        expected = routes.AdminDashboardSummaryResponse(
            organizations=3,
            projects=5,
            api_keys=8,
            users=13,
        )
        admin_service.getDashboardSummary = AsyncMock(return_value=expected)

        result = await routes.get_admin_dashboard_summary(
            ADMIN_INFO,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.getDashboardSummary.assert_awaited_once_with()

    async def test_list_admin_projects_passes_pagination_to_service(self):
        admin_service = Mock()
        pagination = routes.AdminPaginationQuery(
            limit=5,
            offset=10,
            q="clinic",
        )
        expected = routes.ProjectListResponse(total=0, results=[])
        admin_service.listProjects = AsyncMock(return_value=expected)

        result = await routes.list_admin_projects(
            ADMIN_INFO,
            "org-1",
            pagination,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.listProjects.assert_awaited_once_with(
            "org-1",
            pagination,
        )

    async def test_list_admin_organizations_delegates_to_admin_service(self):
        admin_service = Mock()
        pagination = routes.AdminPaginationQuery(limit=10, offset=5, q="org")
        expected = routes.OrgListResponse(
            total=1,
            results=[
                routes.OrgInfoResponse(
                    org_id="org-1",
                    name="Org 1",
                    owner_id=None,
                )
            ],
        )
        admin_service.listOrganizations = AsyncMock(return_value=expected)

        result = await routes.list_admin_organizations(
            ADMIN_INFO,
            pagination,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.listOrganizations.assert_awaited_once_with(pagination)

    async def test_create_admin_project_delegates_to_admin_service(self):
        admin_service = Mock()
        input_data = routes.CreateProjectRequest(
            name="Project 1",
            description="desc",
        )
        expected = routes.ProjectInfoResponse(
            project_uuid="project-1",
            name="Project 1",
            description="desc",
            organization_id="org-1",
            archived=False,
        )
        admin_service.createProject = AsyncMock(return_value=expected)

        result = await routes.create_admin_project(
            ADMIN_INFO,
            "org-1",
            input_data,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.createProject.assert_awaited_once_with(
            "org-1", input_data
        )

    async def test_delete_admin_api_key_returns_200_after_service_delete(self):
        admin_service = Mock()
        admin_service.deleteApiKey = AsyncMock(return_value=True)

        response = await routes.delete_admin_api_key(
            ADMIN_INFO,
            123,
            admin_service,
        )

        self.assertEqual(response.status_code, 200)
        admin_service.deleteApiKey.assert_awaited_once_with(123)

    async def test_get_admin_api_key_passes_disabled_query_to_service(self):
        admin_service = Mock()
        expected = routes.ApiKeyResponse(
            api_key_id=11,
            api_key_uuid="api-key-1",
            project_id=7,
            project_uuid="project-1",
            name="Key",
            description="",
            hint="sk_x...abcd",
            created_at=datetime.now(UTC),
            permissions=["objects:read"],
            disabled=False,
        )
        admin_service.getApiKey = AsyncMock(return_value=expected)

        result = await routes.get_admin_api_key(
            ADMIN_INFO,
            "api-key-1",
            admin_service,
            disabled=True,
        )

        self.assertEqual(result, expected)
        admin_service.getApiKey.assert_awaited_once_with(
            "api-key-1",
            disabled=True,
        )

    async def test_get_user_profile_delegates_to_admin_service(self):
        admin_service = Mock()
        expected = routes.AdminUserProfileResponse(
            user_id="user-1",
            username="alice",
            email="alice@test",
            first_name="Alice",
            last_name="Nguyen",
            enabled=True,
            email_verified=True,
            organizations=[],
            permissions=routes.AdminUserPermissionSummaryResponse(
                organization_permissions=[],
                effective_organization_permissions=[],
                project_permissions=[],
            ),
        )
        admin_service.getUserProfile = AsyncMock(return_value=expected)

        result = await routes.get_user_profile(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.getUserProfile.assert_awaited_once_with("user-1")

    async def test_get_user_permissions_delegates_to_admin_service(self):
        admin_service = Mock()
        expected = routes.AdminUserPermissionSummaryResponse(
            organization_permissions=["organization.settings.read"],
            effective_organization_permissions=["organization.settings.read"],
            project_permissions=[],
        )
        admin_service.getUserPermissions = AsyncMock(return_value=expected)

        result = await routes.get_user_permissions(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.getUserPermissions.assert_awaited_once_with("user-1")

    async def test_set_user_permissions_delegates_to_admin_service(self):
        admin_service = Mock()
        payload = routes.AdminUserPermissionUpdateRequest(
            organization_permissions=["organization.settings.read"],
            project_permissions=[],
        )
        expected = routes.AdminUserProfileResponse(
            user_id="user-1",
            username="alice",
            email="alice@test",
            first_name=None,
            last_name=None,
            enabled=True,
            email_verified=True,
            organizations=[],
            permissions=routes.AdminUserPermissionSummaryResponse(
                organization_permissions=["organization.settings.read"],
                effective_organization_permissions=[
                    "organization.settings.read"
                ],
                project_permissions=[],
            ),
        )
        admin_service.setUserPermissions = AsyncMock(return_value=expected)

        result = await routes.set_user_permissions(
            ADMIN_INFO,
            "user-1",
            payload,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.setUserPermissions.assert_awaited_once_with(
            "user-1",
            payload,
        )

    async def test_set_admin_organization_user_permissions_delegates_scope(
        self,
    ):
        admin_service = Mock()
        payload = routes.UserPermissionsRequest(
            permissions=["organization.settings.read"],
        )
        expected = routes.AdminUserProfileResponse(
            user_id="user-1",
            username="alice",
            email="alice@test",
            first_name=None,
            last_name=None,
            enabled=True,
            email_verified=True,
            organizations=[],
            permissions=routes.AdminUserPermissionSummaryResponse(
                organization_permissions=["organization.settings.read"],
                effective_organization_permissions=[
                    "organization.settings.read"
                ],
                project_permissions=[],
            ),
        )
        admin_service.setUserOrganizationPermissions = AsyncMock(
            return_value=expected
        )

        result = await routes.set_admin_organization_user_permissions(
            ADMIN_INFO,
            "org-1",
            "user-1",
            payload,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.setUserOrganizationPermissions.assert_awaited_once_with(
            "user-1",
            "org-1",
            ["organization.settings.read"],
        )

    async def test_set_admin_project_user_permissions_delegates_scope(self):
        admin_service = Mock()
        payload = routes.ProjectUserPermissionsRequest(
            permissions=["project.settings.write"],
        )
        expected = routes.AdminUserProfileResponse(
            user_id="user-1",
            username="alice",
            email="alice@test",
            first_name=None,
            last_name=None,
            enabled=True,
            email_verified=True,
            organizations=[],
            permissions=routes.AdminUserPermissionSummaryResponse(
                organization_permissions=[],
                effective_organization_permissions=[],
                project_permissions=[
                    {
                        "project_uuid": "project-1",
                        "permissions": ["project.settings.write"],
                        "effective_permissions": ["project.settings.write"],
                    }
                ],
            ),
        )
        admin_service.setUserProjectPermissions = AsyncMock(
            return_value=expected
        )

        result = await routes.set_admin_project_user_permissions(
            ADMIN_INFO,
            "project-1",
            "user-1",
            payload,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.setUserProjectPermissions.assert_awaited_once_with(
            "user-1",
            "project-1",
            ["project.settings.write"],
        )

    async def test_create_admin_api_key_passes_admin_identity_to_service(self):
        admin_service = Mock()
        now = datetime.now(UTC)
        payload = routes.ApiKeyWriteRequest(
            name="Key",
            description="",
            permissions=["objects:read"],
        )
        expected = routes.ApiKeyCreateResponse(
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
        admin_service.createApiKey = AsyncMock(return_value=expected)

        result = await routes.create_admin_api_key(
            ADMIN_INFO,
            "project-1",
            payload,
            admin_service,
        )

        self.assertEqual(result, expected)
        admin_service.createApiKey.assert_awaited_once_with(
            ADMIN_INFO,
            "project-1",
            payload,
        )

    async def test_admin_api_key_routes_pass_disabled_filter_and_update_field(
        self,
    ):
        admin_service = Mock()
        update_payload = routes.ApiKeyUpdateRequest(
            name="Key",
            description="",
            permissions=["objects:read"],
            disabled=True,
        )
        admin_service.listApiKeys = AsyncMock(return_value="listed")
        admin_service.updateApiKey = AsyncMock(return_value="updated")

        list_result = await routes.list_admin_api_keys(
            ADMIN_INFO,
            "project-1",
            admin_service,
            disabled=True,
        )
        update_result = await routes.update_admin_api_key(
            ADMIN_INFO,
            "api-key-1",
            update_payload,
            admin_service,
        )

        self.assertEqual(list_result, "listed")
        self.assertEqual(update_result, "updated")
        admin_service.listApiKeys.assert_awaited_once_with(
            "project-1",
            disabled=True,
        )
        admin_service.updateApiKey.assert_awaited_once_with(
            "api-key-1",
            update_payload,
        )

    async def test_alias_routes_delegate_to_same_admin_service_methods(self):
        admin_service = Mock()
        pagination = routes.AdminPaginationQuery(limit=10, offset=0, q=None)
        users = routes.OrgUserListResponse(total=0, results=[])
        projects = routes.ProjectUserListResponse(total=0, results=[])
        orgs = []
        profile = routes.AdminUserProfileResponse(
            user_id="user-1",
            username="alice",
            email="alice@test",
            first_name=None,
            last_name=None,
            enabled=True,
            email_verified=True,
            organizations=[],
            permissions=routes.AdminUserPermissionSummaryResponse(
                organization_permissions=[],
                effective_organization_permissions=[],
                project_permissions=[],
            ),
        )
        payload = routes.AdminUserPermissionUpdateRequest(
            organization_permissions=[],
            project_permissions=[],
        )
        admin_service.listOrganizationUsers = AsyncMock(return_value=users)
        admin_service.listProjectUsers = AsyncMock(return_value=projects)
        admin_service.getUserOrganizations = AsyncMock(return_value=orgs)
        admin_service.getUserProfile = AsyncMock(return_value=profile)
        admin_service.getUserPermissions = AsyncMock(
            return_value=profile.permissions
        )
        admin_service.setUserPermissions = AsyncMock(return_value=profile)
        admin_service.resetUserPermissions = AsyncMock(return_value=profile)

        await routes.list_admin_organization_users(
            ADMIN_INFO,
            "org-1",
            pagination,
            admin_service,
        )
        await routes.list_admin_project_users(
            ADMIN_INFO,
            "project-1",
            pagination,
            admin_service,
        )
        await routes.get_user_organizations(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )
        await routes.get_user_profile(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )
        await routes.get_user_permissions(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )
        await routes.set_user_permissions(
            ADMIN_INFO,
            "user-1",
            payload,
            admin_service,
        )
        await routes.reset_user_permissions(
            ADMIN_INFO,
            "user-1",
            admin_service,
        )

        admin_service.listOrganizationUsers.assert_awaited_once_with(
            "org-1",
            pagination,
        )
        admin_service.listProjectUsers.assert_awaited_once_with(
            "project-1",
            pagination,
        )
        admin_service.getUserOrganizations.assert_awaited_once_with("user-1")
        admin_service.getUserProfile.assert_awaited_once_with("user-1")
        admin_service.getUserPermissions.assert_awaited_once_with("user-1")
        admin_service.setUserPermissions.assert_awaited_once_with(
            "user-1",
            payload,
        )
        admin_service.resetUserPermissions.assert_awaited_once_with("user-1")
