import os
import json
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok
from starlette.requests import Request


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_key.dependencies import (
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
    async def test_required_permissions_registers_and_verifies(self):
        dependency = requiredPermissions(["chat.read"])
        service = Mock()
        service.verifyApiKey = AsyncMock(
            return_value=Ok(
                {
                    "api_key_id": 1,
                    "api_key_uuid": "api-key-uuid",
                    "user_uuid": "u1",
                    "project_id": 2,
                    "project_uuid": "proj-uuid",
                    "organization_uuid": "org-uuid",
                    "hashed_key": "hashed",
                    "permissions": ["chat.read"],
                    "rpm_limit_organization": 100,
                    "rpm_limit_project": -1,
                    "spending_limit_organization": -1,
                    "spending_limit_project": -1,
                }
            )
        )
        service.rateLimit = AsyncMock(return_value=Ok(None))
        request = _make_request()

        result = await dependency("raw-key", service)

        self.assertEqual(result["api_key_uuid"], "api-key-uuid")
        service.verifyApiKey.assert_awaited_once_with("raw-key", ["chat.read"])
        service.rateLimit.assert_awaited_once_with(result)

    async def test_get_api_key_info_sets_headers_from_parsed_info(self):
        service = Mock()
        service.parseApiKey = AsyncMock(
            return_value=Ok(
                {
                    "api_key_id": 1,
                    "api_key_uuid": "api-key-uuid",
                    "user_uuid": "u1",
                    "project_id": 2,
                    "project_uuid": "proj-uuid",
                    "organization_uuid": "org-uuid",
                    "hashed_key": "hashed",
                    "permissions": ["chat.run"],
                    "rpm_limit_organization": 50,
                    "rpm_limit_project": -1,
                    "spending_limit_organization": 1000,
                    "spending_limit_project": 500,
                }
            )
        )
        service.rateLimit = AsyncMock(return_value=Ok(None))
        request = _make_request()

        result = await getApiKeyInfo("raw-key", service)

        self.assertEqual(result["api_key_uuid"], "api-key-uuid")
        service.parseApiKey.assert_awaited_once_with("raw-key")
        service.rateLimit.assert_awaited_once_with(result)
