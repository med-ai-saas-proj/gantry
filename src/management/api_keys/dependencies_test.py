import os
import unittest
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.api_keys.permissions import (
    listPermissions,
    clearPermissions,
)
from src.management.api_keys.dependencies import requiredPermissions


class TestApiKeyDependencies(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clearPermissions()

    async def test_required_permissions_registers_and_verifies(self):
        dependency = requiredPermissions(["chat.read"])
        service = Mock()
        service.verifyApiKey = AsyncMock(
            return_value=Ok({"api_key_id": 1, "user_id": "u1"})
        )

        result = await dependency("raw-key", service)

        self.assertEqual(result["api_key_id"], 1)
        self.assertEqual(listPermissions(), ["chat.read"])
        service.verifyApiKey.assert_awaited_once_with("raw-key", ["chat.read"])
