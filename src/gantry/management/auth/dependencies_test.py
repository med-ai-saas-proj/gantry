import os
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.auth.services import MissingOrganizationClaimError
from gantry.management.auth.dependencies import (
    MissingOrganizationContextError,
    _getUserInfo,
    _getAdminInfo,
    getUserOrgUuid,
    requireUserOrgUuid,
)


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_unwraps_verified_token(self):
        auth_service = Mock()
        auth_service.verifyToken = AsyncMock(
            return_value=Ok(
                {
                    "id": "u1",
                    "username": "alice",
                    "email": "a@test",
                    "org_uuid": "org-1",
                    "org_permissions": ["organization.settings.read"],
                    "project_permissions": {"proj-1": ["project.owner"]},
                }
            )
        )

        user_info = await _getUserInfo("token", auth_service)

        self.assertEqual(user_info["org_uuid"], "org-1")
        self.assertEqual(
            user_info["project_permissions"],
            {"proj-1": ["project.owner"]},
        )

    async def test_get_user_info_propagates_missing_organization_claim(self):
        auth_service = Mock()
        auth_service.verifyToken = AsyncMock(
            return_value=Err(MissingOrganizationClaimError())
        )

        with self.assertRaises(MissingOrganizationClaimError):
            await _getUserInfo("token", auth_service)

    async def test_get_admin_info_unwraps_admin_token(self):
        auth_service = Mock()
        auth_service.verifyTokenAdmin.return_value = Ok(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
            }
        )

        user_info = await _getAdminInfo("token", auth_service)

        self.assertEqual(user_info["id"], "admin-1")

    async def test_get_user_org_uuid(self):
        user_info = {
            "id": "u1",
            "username": "alice",
            "email": "a@test",
            "org_uuid": "org-1",
            "org_permissions": [],
            "project_permissions": {},
        }
        self.assertEqual(await getUserOrgUuid(user_info), "org-1")
        self.assertEqual(await requireUserOrgUuid("org-1"), "org-1")
        with self.assertRaises(MissingOrganizationContextError):
            await requireUserOrgUuid("")
