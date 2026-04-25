import os
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.auth.services import (
    InsufficientPermissionsError,
    MissingOrganizationClaimError,
)
from gantry.management.auth.dependencies import (
    MissingOrganizationContextError,
    getUserInfo,
    _getUserInfo,
    getUserOrgId,
    getAdminUserInfo,
    requireUserOrgId,
    _getAdminUserInfo,
)


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_resolves_claim_org_id_from_memberships(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": ["proj-1:project.owner"],
                "org_id": "11111111-1111-1111-1111-111111111111",
                "project_ids": ["proj-1"],
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "org-name",
                        "alias": "org-alias",
                    }
                ]
            )
        )

        user_info = await _getUserInfo(
            "token",
            auth_service,
            kc_org_client,
        )

        self.assertEqual(
            user_info["org_id"], "11111111-1111-1111-1111-111111111111"
        )
        self.assertEqual(user_info["project_ids"], ["proj-1"])
        kc_org_client.getMemberOrganizations.assert_awaited_once_with("u1")

    async def test_get_user_info_resolves_org_name_claim_to_org_id(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "org-name",
                "project_ids": [],
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok(
                [{"id": "org-1", "name": "org-name", "alias": "org-alias"}]
            )
        )

        user_info = await _getUserInfo(
            "token",
            auth_service,
            kc_org_client,
        )

        self.assertEqual(user_info["org_id"], "org-1")

    async def test_get_user_info_rejects_regular_user_without_org(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Err(
            MissingOrganizationClaimError()
        )
        kc_org_client = Mock()

        with self.assertRaises(MissingOrganizationClaimError):
            await _getUserInfo(
                "token",
                auth_service,
                kc_org_client,
            )

    async def test_get_user_info_keeps_project_ids_from_verify_token(
        self,
    ):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [
                    "proj-1:project.settings.read",
                    "proj-2:project.owner",
                ],
                "org_id": "org-1",
                "project_ids": ["proj-1", "proj-2"],
            }
        )
        kc_org_client = Mock()
        kc_org_client.getMemberOrganizations = AsyncMock(
            return_value=Ok([{"id": "org-1", "name": "org-name"}])
        )

        user_info = await _getUserInfo(
            "token",
            auth_service,
            kc_org_client,
        )

        self.assertEqual(user_info["project_ids"], ["proj-1", "proj-2"])

    async def test_get_admin_user_info_requires_admin_role(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@test",
                "roles": ["ADMIN"],
                "org_id": "",
                "project_ids": [],
            }
        )
        auth_service.checkAdminRole.return_value = Ok(None)

        user_info = await _getAdminUserInfo("token", auth_service)

        self.assertEqual(user_info["id"], "admin-1")
        auth_service.checkAdminRole.assert_called_once_with(user_info)

    async def test_get_admin_user_info_rejects_missing_admin_role(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "",
                "project_ids": [],
            }
        )
        auth_service.checkAdminRole.side_effect = InsufficientPermissionsError(
            ["ADMIN"]
        )

        with self.assertRaises(InsufficientPermissionsError):
            await _getAdminUserInfo("token", auth_service)

    async def test_get_user_org_id_and_require_user_org_id(self):
        self.assertEqual(
            (
                await getUserOrgId(
                    {
                        "id": "u1",
                        "roles": [],
                        "org_id": "org-1",
                        "project_ids": [],
                    }
                )
            ),
            "org-1",
        )
        self.assertEqual(await requireUserOrgId("org-1"), "org-1")
        with self.assertRaises(MissingOrganizationContextError):
            await requireUserOrgId("")
