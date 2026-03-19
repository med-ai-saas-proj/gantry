import os
import unittest
from unittest.mock import AsyncMock, Mock

from safe_result import Err, Ok

os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.auth.dependencies import (
    MissingOrganizationContextError,
    getUserInfo,
    getUserOrgId,
    requireUserOrgId,
)
from src.management.auth.services import MissingOrganizationClaimError


class _DummyErr(Exception):
    pass


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_resolves_claim_org_id_from_memberships(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "11111111-1111-1111-1111-111111111111",
            }
        )
        kc_org_client = Mock()
        kc_org_client.get_member_organizations = AsyncMock(
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

        user_info = await getUserInfo("token", auth_service, kc_org_client)

        self.assertEqual(
            user_info["org_id"], "11111111-1111-1111-1111-111111111111"
        )
        kc_org_client.get_member_organizations.assert_awaited_once_with("u1")

    async def test_get_user_info_resolves_org_name_claim_to_org_id(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "org-name",
            }
        )
        kc_org_client = Mock()
        kc_org_client.get_member_organizations = AsyncMock(
            return_value=Ok(
                [{"id": "org-1", "name": "org-name", "alias": "org-alias"}]
            )
        )

        user_info = await getUserInfo("token", auth_service, kc_org_client)

        self.assertEqual(user_info["org_id"], "org-1")

    async def test_get_user_info_rejects_regular_user_without_org(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Err(
            MissingOrganizationClaimError()
        )
        kc_org_client = Mock()

        with self.assertRaises(MissingOrganizationClaimError):
            await getUserInfo("token", auth_service, kc_org_client)

    async def test_get_user_org_id_and_require_user_org_id(self):
        self.assertEqual(
            await getUserOrgId({"id": "u1", "roles": [], "org_id": "org-1"}),
            "org-1",
        )
        self.assertIsNone(
            await getUserOrgId({"id": "u1", "roles": [], "org_id": None})
        )
        self.assertEqual(await requireUserOrgId("org-1"), "org-1")
        with self.assertRaises(MissingOrganizationContextError):
            await requireUserOrgId(None)
