from pyrusult import Ok

import os
import unittest
from unittest.mock import Mock, AsyncMock


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.management.api_key import routes
from gantry.management.api_key.dtos import (
    ApiKeyWriteRequest,
    ApiKeyUpdateRequest,
)
from gantry.management.project.permissions import ProjectPermission


class TestApiKeyRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_permission_route_returns_catalog(self):
        apikey_service = Mock()
        apikey_service.getPermissionCatalog = Mock(return_value="catalog")
        user_info = {"id": "u1", "roles": [], "org_id": "org-1"}

        self.assertEqual(
            await routes.getApiKeyPermissions(user_info, apikey_service),
            "catalog",
        )

    async def test_query_scoped_routes_authorize_then_call_service(self):
        apikey_service = Mock()
        apikey_service.getApiKeys = AsyncMock(return_value=Ok("listed"))
        apikey_service.createApiKey = AsyncMock(return_value=Ok("created"))
        project_service = Mock()
        project_service.authorizeProjectPermission = AsyncMock(
            return_value=Ok(True)
        )
        user_info = {"id": "u1", "roles": [], "org_id": "org-1"}

        self.assertEqual(
            await routes.getApiKeys(
                user_info, "proj-1", apikey_service, project_service
            ),
            "listed",
        )
        self.assertEqual(
            await routes.createApiKey(
                user_info,
                "proj-1",
                ApiKeyWriteRequest(
                    name="Key 1",
                    description="desc",
                    permissions=["chat.run"],
                ),
                apikey_service,
                project_service,
            ),
            "created",
        )
        self.assertEqual(
            project_service.authorizeProjectPermission.await_count,
            2,
        )
        project_service.authorizeProjectPermission.assert_any_await(
            project_uuid="proj-1",
            user_id="u1",
            required=ProjectPermission.APIKEY_READ,
        )
        project_service.authorizeProjectPermission.assert_any_await(
            project_uuid="proj-1",
            user_id="u1",
            required=ProjectPermission.APIKEY_WRITE,
        )

    async def test_uuid_routes_authorize_via_resolved_project(self):
        apikey_service = Mock()
        apikey_service.getApiKeyProjectUuid = AsyncMock(
            return_value=Ok("proj-1")
        )
        apikey_service.getApiKey = AsyncMock(return_value=Ok("detail"))
        apikey_service.updateApiKey = AsyncMock(return_value=Ok("updated"))
        apikey_service.setApiKeyDisabled = AsyncMock(
            side_effect=[Ok("disabled"), Ok("enabled")]
        )
        apikey_service.deleteApiKey = AsyncMock(return_value=Ok(True))
        project_service = Mock()
        project_service.authorizeProjectPermission = AsyncMock(
            return_value=Ok(True)
        )
        user_info = {"id": "u1", "roles": [], "org_id": "org-1"}

        self.assertEqual(
            await routes.getApiKey(
                user_info, "api-key-11", apikey_service, project_service
            ),
            "detail",
        )
        self.assertEqual(
            await routes.updateApiKey(
                user_info,
                "api-key-11",
                ApiKeyUpdateRequest(
                    name="Key 1",
                    description="desc",
                    permissions=["chat.run"],
                    disabled=True,
                ),
                apikey_service,
                project_service,
            ),
            "updated",
        )
        apikey_service.updateApiKey.assert_awaited_once_with(
            api_key_uuid="api-key-11",
            name="Key 1",
            description="desc",
            permissions=["chat.run"],
            disabled=True,
        )
        delete_res = await routes.deleteApiKey(
            user_info, "api-key-11", apikey_service, project_service
        )
        self.assertEqual(delete_res.status_code, 200)
        self.assertEqual(
            await routes.disableApiKey(
                user_info, "api-key-11", apikey_service, project_service
            ),
            "disabled",
        )
        self.assertEqual(
            await routes.enableApiKey(
                user_info, "api-key-11", apikey_service, project_service
            ),
            "enabled",
        )
