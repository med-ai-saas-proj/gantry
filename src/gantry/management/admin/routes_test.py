from gantry.management.admin import routes

import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok


class TestAdminRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_get_admin_me_returns_admin_identity(self):
        result = await routes.get_admin_me(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            }
        )

        self.assertEqual(result.id, "admin-1")
        self.assertEqual(result.roles, ["ADMIN"])

    async def test_get_user_organizations_returns_keycloak_memberships(self):
        kc = Mock()
        kc.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [
                    {"id": "org-1", "name": "Org 1", "alias": "org-1"},
                    {"id": "org-2", "name": "Org 2"},
                ]
            )
        )

        result = await routes.get_user_organizations(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            },
            "user-1",
            kc,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, "org-1")
        kc.getMemberOrganizations.assert_awaited_once_with("user-1")

    async def test_get_user_profile_returns_profile_and_permissions(self):
        kc = Mock()
        kc.getUserProfile = AsyncMock(
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
        kc.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [{"id": "org-1", "name": "Org 1", "alias": "org-1"}]
            )
        )

        result = await routes.get_user_profile(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            },
            "user-1",
            kc,
        )

        self.assertEqual(result.id, "user-1")
        self.assertEqual(result.username, "alice")
        self.assertTrue(result.enabled)
        self.assertEqual(len(result.organizations), 1)
        self.assertEqual(
            result.permissions.organization_permissions,
            ["organization.owner"],
        )
        self.assertIn(
            "organization.settings.read",
            result.permissions.effective_organization_permissions,
        )
        self.assertEqual(len(result.permissions.project_permissions), 2)
        self.assertEqual(
            result.permissions.project_permissions[0].project_id,
            "project-a",
        )
        self.assertIn(
            "project.users.add",
            result.permissions.project_permissions[0].effective_permissions,
        )
        kc.getUserProfile.assert_awaited_once_with("user-1")
        kc.getMemberOrganizations.assert_awaited_once_with("user-1")

    async def test_set_user_permissions_updates_keycloak_and_returns_profile(
        self,
    ):
        kc = Mock()
        kc.setUserAttributes = AsyncMock(return_value=Ok(True))
        kc.getUserProfile = AsyncMock(
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
        kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))

        result = await routes.set_user_permissions(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            },
            "user-1",
            routes.AdminUserPermissionUpdateRequest(
                organization_permissions=["organization.settings.read"],
                project_permissions=[
                    routes.AdminUserProjectPermissionUpdateRequest(
                        project_id="project-a",
                        permissions=["project.settings.read"],
                    )
                ],
            ),
            kc,
        )

        self.assertEqual(result.id, "user-1")
        kc.setUserAttributes.assert_awaited_once_with(
            "user-1",
            {
                "org_permissions": ["organization.settings.read"],
                "project_permissions": {"project-a": ["project.settings.read"]},
            },
        )

    async def test_reset_user_permissions_clears_keycloak_attributes(self):
        kc = Mock()
        kc.setUserAttributes = AsyncMock(return_value=Ok(True))
        kc.getUserProfile = AsyncMock(
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
        kc.getMemberOrganizations = AsyncMock(return_value=Ok([]))

        result = await routes.reset_user_permissions(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            },
            "user-1",
            kc,
        )

        self.assertEqual(result.permissions.organization_permissions, [])
        kc.setUserAttributes.assert_awaited_once_with(
            "user-1",
            {
                "org_permissions": [],
                "project_permissions": {},
            },
        )

    async def test_set_user_permissions_rejects_invalid_org_permission(self):
        kc = Mock()

        with self.assertRaises(routes.InvalidAdminPermissionError):
            await routes.set_user_permissions(
                {
                    "id": "admin-1",
                    "username": "admin",
                    "email": "admin@test",
                    "roles": ["ADMIN"],
                    "org_id": "",
                    "project_ids": [],
                },
                "user-1",
                routes.AdminUserPermissionUpdateRequest(
                    organization_permissions=["organization.nope"],
                    project_permissions=[],
                ),
                kc,
            )

        kc.setUserAttributes.assert_not_called()

    async def test_set_user_permissions_rejects_invalid_project_permission(
        self,
    ):
        kc = Mock()

        with self.assertRaises(routes.InvalidAdminPermissionError):
            await routes.set_user_permissions(
                {
                    "id": "admin-1",
                    "username": "admin",
                    "email": "admin@test",
                    "roles": ["ADMIN"],
                    "org_id": "",
                    "project_ids": [],
                },
                "user-1",
                routes.AdminUserPermissionUpdateRequest(
                    organization_permissions=[],
                    project_permissions=[
                        routes.AdminUserProjectPermissionUpdateRequest(
                            project_id="project-a",
                            permissions=["project.nope"],
                        )
                    ],
                ),
                kc,
            )

        kc.setUserAttributes.assert_not_called()
