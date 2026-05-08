import os
import unittest
from types import SimpleNamespace
from datetime import datetime
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, ResultStatus


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.settings.api_key import ApiKeyPermission
from gantry.management.api_key.services import (
    ApiKeyService,
    InvalidAPIKey,
    UserNotFoundError,
    ApiKeyDisabledError,
    ApiKeyNotFoundError,
    InsufficientPermission,
    InvalidPermissionError,
)
from gantry.management.project.services import ProjectNotFoundError


class _DummySessionManager:
    def __init__(self):
        self.session = Mock()
        self.session.commit = AsyncMock()

    @asynccontextmanager
    async def get_session(self):
        yield self.session


class TestApiKeyService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.created_at = datetime(2026, 3, 28, 13, 0, 0)
        self.session_manager = _DummySessionManager()
        self.api_key_repo = Mock()
        self.project_repo = Mock()
        self.api_key_repo.getByUuid = AsyncMock(return_value=None)
        self.api_key_repo.getContextByHashedKey = AsyncMock(return_value=None)
        self.api_key_repo.updateById = AsyncMock(return_value=None)
        self.api_key_repo.updateDisabledByUuid = AsyncMock(return_value=None)
        self.api_key_repo.deleteByUuid = AsyncMock(return_value=False)
        self.api_key_repo.listDistinctPermissions = AsyncMock(return_value=[])
        self.service = ApiKeyService(
            config={"key_secret": "secret", "api_key_secret_length": 8},
            logger=Mock(),
            api_key_repo=self.api_key_repo,
            project_repo=self.project_repo,
            permissions=[
                ApiKeyPermission(
                    id="chat.run", name="chat.run", description=""
                ),
                ApiKeyPermission(
                    id="chat.read", name="chat.read", description=""
                ),
            ],
            session_manager=self.session_manager,
        )
        self.service.default_org_rate_limit = 120

    def _context(self, **overrides):
        context = {
            "api_key_id": 11,
            "api_key_uuid": "demo",
            "user_uuid": "u1",
            "project_id": 7,
            "org_id": "org-1",
            "organization_uuid": "org-1",
            "project_uuid": "proj-1",
            "hashed_key": "hashed",
            "permissions": ["chat.run", "chat.read"],
            "disabled": False,
            "rpm_limit_organization": 90,
            "rpm_limit_project": -1,
            "spending_limit_organization": -1,
            "spending_limit_project": -1,
        }
        context.update(overrides)
        return context

    async def test_create_api_key_returns_created_resource_with_raw_key(self):
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        created = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            name="k1",
            description="desc",
            hint="sk_ab...cdef",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.project_repo.getByUuid = AsyncMock(return_value=project)
        self.api_key_repo.create = AsyncMock(return_value=created)

        result = await self.service.createApiKey(
            actor_user_id="u1",
            project_uuid="proj-1",
            name="k1",
            description="desc",
            permissions=["chat.run"],
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap().api_key_uuid, "api-key-11")
        self.assertEqual(result.unwrap().project_uuid, "proj-1")
        self.assertEqual(result.unwrap().permissions, ["chat.run"])
        self.assertTrue(result.unwrap().key.startswith("sk_"))
        self.session_manager.session.commit.assert_awaited_once()

    async def test_create_api_key_rejects_unknown_permissions(self):
        result = await self.service.createApiKey(
            actor_user_id="u1",
            project_uuid="proj-1",
            name="k1",
            description="desc",
            permissions=["unknown.permission"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidPermissionError)

    async def test_create_api_key_returns_project_not_found(self):
        self.project_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.createApiKey(
            actor_user_id="u1",
            project_uuid="proj-404",
            name="k1",
            description="desc",
            permissions=["chat.run"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_get_api_keys_lists_all_keys_for_project(self):
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        api_key = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.project_repo.getByUuid = AsyncMock(return_value=project)
        self.api_key_repo.getByProjectId = AsyncMock(return_value=[api_key])
        self.api_key_repo.countByProjectId = AsyncMock(return_value=1)

        result = await self.service.getApiKeys(project_uuid="proj-1")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap().total, 1)
        self.assertEqual(result.unwrap().results[0].api_key_uuid, "api-key-11")
        self.assertEqual(result.unwrap().results[0].project_uuid, "proj-1")

    async def test_get_api_keys_returns_project_not_found(self):
        self.project_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.getApiKeys(project_uuid="proj-404")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_get_api_key_by_id_returns_project_scoped_response(self):
        api_key = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByUuid = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.getApiKey("api-key-11")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap().api_key_uuid, "api-key-11")
        self.assertEqual(result.unwrap().project_uuid, "proj-1")

    async def test_get_api_key_returns_not_found_from_lookup(self):
        self.api_key_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.getApiKey("api-key-11")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_get_api_key_returns_project_not_found_when_owner_project_missing(
        self,
    ):
        api_key = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByUuid = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKey("api-key-11")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_update_api_key_rejects_missing_key(self):
        self.api_key_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["chat.run"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_update_api_key_rejects_unknown_permissions(self):
        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["unknown.permission"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidPermissionError)

    async def test_update_api_key_returns_updated_response(self):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        updated = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="updated",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.read"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap().permissions, ["chat.read"])
        self.session_manager.session.commit.assert_awaited_once()

    async def test_update_api_key_returns_not_found_when_update_loses_row(self):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_update_api_key_returns_project_not_found_when_owner_project_missing(
        self,
    ):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        updated = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="updated",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.read"],
            disabled=False,
        )
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_delete_api_key_returns_not_found_for_missing_key(self):
        self.api_key_repo.deleteByUuid = AsyncMock(return_value=False)

        self.api_key_repo.getByUuid = AsyncMock(return_value=None)
        result = await self.service.deleteApiKey("api-key-11")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_delete_api_key_commits_on_success(self):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
            hashed_key="hashed",
        )
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.deleteByUuid = AsyncMock(return_value=True)

        result = await self.service.deleteApiKey("api-key-11")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertTrue(result.unwrap())
        self.session_manager.session.commit.assert_awaited_once()

    async def test_set_api_key_disabled_returns_updated_response(self):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        updated = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=True,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.updateDisabledByUuid = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.setApiKeyDisabled(
            api_key_uuid="api-key-11", disabled=True
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertTrue(result.unwrap().disabled)
        self.session_manager.session.commit.assert_awaited_once()

    async def test_verify_api_key_returns_runtime_context(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context()
        )

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap()["api_key_uuid"], "demo")
        self.assertEqual(result.unwrap()["project_uuid"], "proj-1")
        self.assertEqual(result.unwrap()["organization_uuid"], "org-1")
        self.assertEqual(result.unwrap()["user_uuid"], "u1")
        self.assertEqual(
            result.unwrap()["permissions"], ["chat.run", "chat.read"]
        )
        self.assertEqual(result.unwrap()["rpm_limit_organization"], 90)
        self.assertEqual(result.unwrap()["spending_limit_project"], -1)
        self.assertEqual(result.unwrap()["spending_limit_organization"], -1)

    async def test_verify_api_key_allows_empty_required_permissions(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context()
        )

        result = await self.service.verifyApiKey("sk_demo.secret", [])

        self.assertEqual(result.status, ResultStatus.Ok)

    async def test_verify_api_key_rejects_unknown_key(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(return_value=None)

        result = await self.service.verifyApiKey(
            "sk_missing.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidAPIKey)

    async def test_verify_api_key_rejects_disabled_key(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context(disabled=True)
        )

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyDisabledError)

    async def test_verify_api_key_rejects_missing_user_id(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context(user_uuid="")
        )

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), UserNotFoundError)

    async def test_verify_api_key_rejects_missing_permission(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context(permissions=["chat.run"])
        )

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InsufficientPermission)

    async def test_parse_api_key_returns_enriched_runtime_context(self):
        self.api_key_repo.getContextByHashedKey = AsyncMock(
            return_value=self._context(
                permissions=["chat.run"],
            )
        )

        result = await self.service.parseApiKey("sk_demo.secret")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap()["api_key_uuid"], "demo")
        self.assertEqual(result.unwrap()["project_uuid"], "proj-1")
        self.assertEqual(result.unwrap()["rpm_limit_organization"], 90)
        self.assertEqual(result.unwrap()["spending_limit_project"], -1)
        self.assertEqual(result.unwrap()["user_uuid"], "u1")

    async def test_update_api_key_does_not_require_cache_invalidation(self):
        current = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
            hashed_key="hashed",
        )
        updated = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="updated",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.read"],
            disabled=False,
            hashed_key="hashed",
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByUuid = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.updateApiKey(
            api_key_uuid="api-key-11",
            name="updated",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result.status, ResultStatus.Ok)

    async def test_get_api_key_project_uuid_returns_project_uuid(self):
        api_key = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByUuid = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.getApiKeyProjectUuid("api-key-11")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap(), "proj-1")

    async def test_get_api_key_project_uuid_returns_not_found_from_lookup(self):
        self.api_key_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.getApiKeyProjectUuid("api-key-11")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_get_api_key_project_uuid_returns_project_not_found(self):
        api_key = SimpleNamespace(
            id=11,
            uuid="api-key-11",
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByUuid = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKeyProjectUuid("api-key-11")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    def test_internal_get_api_key_parts_parses_prefixed_key(self):
        result = self.service._internalGetApiKeyParts("sk_demo.secret")

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap(), ("demo", "secret"))

    def test_internal_get_api_key_parts_rejects_invalid_prefix(self):
        result = self.service._internalGetApiKeyParts("demo.secret")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidAPIKey)

    def test_internal_get_api_key_parts_rejects_malformed_key(self):
        result = self.service._internalGetApiKeyParts("sk_demo")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidAPIKey)

    def test_get_permission_catalog_returns_registered_permissions(self):
        result = self.service.getPermissionCatalog()

        self.assertEqual(result.total, 2)
        self.assertEqual(
            [permission.id for permission in result.results],
            ["chat.run", "chat.read"],
        )
