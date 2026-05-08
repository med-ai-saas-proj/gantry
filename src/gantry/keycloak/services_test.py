"""Unit tests for the Keycloak service adapter."""

from gantry.keycloak.services import (
    KeycloakOrgError,
    KeycloakServiceClient,
    KeycloakOrgConfigError,
)

import unittest
from unittest.mock import AsyncMock

from pyrusult import ResultStatus


def _client(admin=None) -> KeycloakServiceClient:
    """Build a KeycloakServiceClient without opening a real connection."""
    client = KeycloakServiceClient.__new__(KeycloakServiceClient)
    client.base_url = "http://keycloak"
    client.realm = "gantry"
    client.service_client_id = "svc"
    client.service_client_secret = "secret"
    client._connection = None
    client._admin = admin
    client._init_error = None
    return client


class TestKeycloakServiceClientAdminLists(unittest.IsolatedAsyncioTestCase):
    async def test_list_orgs_forwards_pagination_and_search(self):
        admin = type("Admin", (), {})()
        admin.a_get_organizations = AsyncMock(
            return_value=[{"id": "org-1", "name": "Org 1"}]
        )
        client = _client(admin)

        result = await client.listOrgs(
            first=5,
            max_results=10,
            search="org",
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap()[0]["id"], "org-1")
        admin.a_get_organizations.assert_awaited_once_with(
            query={"first": 5, "max": 10, "search": "org"}
        )

    async def test_list_orgs_rejects_non_list_payload(self):
        admin = type("Admin", (), {})()
        admin.a_get_organizations = AsyncMock(return_value={"id": "org-1"})
        client = _client(admin)

        result = await client.listOrgs()

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), KeycloakOrgError)

    async def test_create_org_returns_created_id(self):
        admin = type("Admin", (), {})()
        admin.a_create_organization = AsyncMock(return_value="org-1")
        client = _client(admin)

        result = await client.createOrg({"name": "Org 1", "alias": "org-1"})

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap(), "org-1")
        admin.a_create_organization.assert_awaited_once_with(
            {"name": "Org 1", "alias": "org-1"}
        )

    async def test_create_org_rejects_missing_location_id(self):
        admin = type("Admin", (), {})()
        admin.a_create_organization = AsyncMock(return_value=None)
        client = _client(admin)

        result = await client.createOrg({"name": "Org 1"})

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), KeycloakOrgError)

    async def test_add_member_uses_keycloak_org_user_add(self):
        admin = type("Admin", (), {})()
        admin.a_organization_user_add = AsyncMock(return_value=b"")
        client = _client(admin)

        result = await client.addMember("org-1", "user-1")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertTrue(result.unwrap())
        admin.a_organization_user_add.assert_awaited_once_with(
            "user-1",
            "org-1",
        )

    async def test_list_users_forwards_pagination_and_search(self):
        admin = type("Admin", (), {})()
        admin.a_get_users = AsyncMock(
            return_value=[{"id": "user-1", "username": "alice"}]
        )
        client = _client(admin)

        result = await client.listUsers(
            first=3,
            max_results=7,
            search="alice",
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap()[0]["username"], "alice")
        admin.a_get_users.assert_awaited_once_with(
            query={"first": 3, "max": 7, "search": "alice"}
        )

    async def test_count_users_forwards_search(self):
        admin = type("Admin", (), {})()
        admin.a_users_count = AsyncMock(return_value=2)
        client = _client(admin)

        result = await client.countUsers(search="alice")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap(), 2)
        admin.a_users_count.assert_awaited_once_with(query={"search": "alice"})

    async def test_count_users_rejects_non_int_payload(self):
        admin = type("Admin", (), {})()
        admin.a_users_count = AsyncMock(return_value="2")
        client = _client(admin)

        result = await client.countUsers()

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), KeycloakOrgError)

    async def test_missing_service_secret_returns_config_error(self):
        client = KeycloakServiceClient(
            server_url="http://keycloak",
            realm="gantry",
            service_client_id="svc",
            service_client_secret="",
        )

        result = await client.listUsers()

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), KeycloakOrgConfigError)


if __name__ == "__main__":
    unittest.main()
