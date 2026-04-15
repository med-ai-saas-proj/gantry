import os
import json
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok
from starlette.requests import Request


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_keys.permissions import (
    listPermissions,
    clearPermissions,
)
from gantry.management.api_keys.dependencies import (
    getApiKeyInfo,
    requiredPermissions,
)


def _make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
    )


class TestApiKeyDependencies(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clearPermissions()

    async def test_required_permissions_registers_and_verifies(self):
        dependency = requiredPermissions(["chat.read"])
        service = Mock()
        service.verifyApiKey = AsyncMock(
            return_value=Ok(
                {
                    "api_key_id": 1,
                    "api_key_uuid": "api-key-uuid",
                    "user_id": "u1",
                    "project_id": 2,
                    "project_uuid": "proj-uuid",
                    "org_id": "org-uuid",
                    "organization_uuid": "org-uuid",
                    "project_uid": "proj-uuid",
                    "hashed_key": "hashed",
                    "permissions": ["chat.read"],
                    "rpm_limit_organization": 100,
                    "rpm_limit_project": -1,
                    "spending_limit_organization": -1,
                    "spending_limit_project": -1,
                }
            )
        )
        request = _make_request()

        result = await dependency(request, "raw-key", service)

        self.assertEqual(result["api_key_id"], 1)
        self.assertEqual(listPermissions(), ["chat.read"])
        service.verifyApiKey.assert_awaited_once_with("raw-key", ["chat.read"])
        self.assertEqual(request.headers["X-Organization-UUID"], "org-uuid")
        self.assertEqual(request.headers["X-Project-UUID"], "proj-uuid")
        self.assertEqual(request.headers["X-API-Key-UUID"], "api-key-uuid")
        self.assertEqual(
            json.loads(request.headers["X-Permissions"]), ["chat.read"]
        )
        self.assertEqual(request.headers["X-RPM-Limit-Organization"], "100")
        self.assertEqual(request.headers["X-RPM-Limit-Project"], "-1")
        self.assertEqual(request.headers["X-Spending-Limit-Organization"], "-1")
        self.assertEqual(request.headers["X-Spending-Limit-Project"], "-1")
        self.assertEqual(
            request.state.api_key_info["api_key_uuid"], "api-key-uuid"
        )

    async def test_get_api_key_info_sets_headers_from_parsed_info(self):
        service = Mock()
        service.parseApiKey = AsyncMock(
            return_value=Ok(
                {
                    "api_key_id": 1,
                    "api_key_uuid": "api-key-uuid",
                    "user_id": "u1",
                    "project_id": 2,
                    "project_uuid": "proj-uuid",
                    "org_id": "org-uuid",
                    "organization_uuid": "org-uuid",
                    "project_uid": "proj-uuid",
                    "hashed_key": "hashed",
                    "permissions": ["chat.run"],
                    "rpm_limit_organization": 50,
                    "rpm_limit_project": -1,
                    "spending_limit_organization": 1000,
                    "spending_limit_project": 500,
                }
            )
        )
        request = _make_request()

        result = await getApiKeyInfo(request, "raw-key", service)

        self.assertEqual(result["api_key_uuid"], "api-key-uuid")
        self.assertEqual(request.headers["X-Organization-UUID"], "org-uuid")
        self.assertEqual(request.headers["X-Project-UUID"], "proj-uuid")
        self.assertEqual(request.headers["X-API-Key-UUID"], "api-key-uuid")
        self.assertEqual(
            json.loads(request.headers["X-Permissions"]), ["chat.run"]
        )
        self.assertEqual(request.headers["X-RPM-Limit-Organization"], "50")
        self.assertEqual(request.headers["X-RPM-Limit-Project"], "-1")
        self.assertEqual(
            request.headers["X-Spending-Limit-Organization"], "1000"
        )
        self.assertEqual(request.headers["X-Spending-Limit-Project"], "500")
        self.assertEqual(
            request.state.api_key_info["project_uuid"], "proj-uuid"
        )
