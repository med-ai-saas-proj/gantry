import os
import unittest
from unittest.mock import AsyncMock, Mock

from safe_result import Ok

os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.auth.dependencies import (
    MissingOrganizationContextError,
    getUserInfo,
    getUserOrgId,
    requireUserOrgId,
)


class _DummyErr(Exception):
    pass


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_get_user_info_keeps_claim_org_id(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
                "org_id": "org-1",
            }
        )
        kc_org_client = Mock()

        user_info = await getUserInfo("token", auth_service, kc_org_client)

        self.assertEqual(user_info["org_id"], "org-1")
        kc_org_client.get_member_organizations.assert_not_called()

    async def test_get_user_info_fetches_org_id_from_membership(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
            }
        )
        kc_org_client = Mock()
        kc_org_client.get_member_organizations = AsyncMock(
            return_value=Ok([{"id": "org-1"}])
        )

        user_info = await getUserInfo("token", auth_service, kc_org_client)

        self.assertEqual(user_info["org_id"], "org-1")

    async def test_get_user_info_returns_none_when_user_has_no_org(self):
        auth_service = Mock()
        auth_service.verifyToken.return_value = Ok(
            {
                "id": "u1",
                "username": "alice",
                "email": "a@test",
                "roles": [],
            }
        )
        kc_org_client = Mock()
        kc_org_client.get_member_organizations = AsyncMock(return_value=Ok([]))

        user_info = await getUserInfo("token", auth_service, kc_org_client)

        self.assertIsNone(user_info.get("org_id"))

    async def test_get_user_info_ignores_lookup_failure_and_service_accounts(self):
        auth_service = Mock()
        auth_service.verifyToken.side_effect = [
            Ok(
                {
                    "id": "u1",
                    "username": "alice",
                    "email": "a@test",
                    "roles": [],
                }
            ),
            Ok(
                {
                    "id": "svc",
                    "username": "service-account-backend",
                    "email": None,
                    "roles": [],
                    "is_service_account": True,
                }
            ),
        ]
        kc_org_client = Mock()
        kc_org_client.get_member_organizations = AsyncMock(
            return_value=Ok([{"name": "missing-id"}])
        )

        user_info = await getUserInfo("token", auth_service, kc_org_client)
        service_account = await getUserInfo("token", auth_service, kc_org_client)

        self.assertIsNone(user_info.get("org_id"))
        self.assertIsNone(service_account["org_id"])

    async def test_get_user_org_id_and_require_user_org_id(self):
        self.assertEqual(
            await getUserOrgId({"id": "u1", "roles": [], "org_id": "org-1"}),
            "org-1",
        )
        self.assertIsNone(await getUserOrgId({"id": "u1", "roles": []}))
        self.assertEqual(await requireUserOrgId("org-1"), "org-1")
        with self.assertRaises(MissingOrganizationContextError):
            await requireUserOrgId(None)
