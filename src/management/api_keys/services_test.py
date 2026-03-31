import os
import unittest
from types import SimpleNamespace
from datetime import datetime
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, ResultStatus


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.project.services import ProjectNotFoundError
from src.management.api_keys.services import (
    ApiKeyService,
    InvalidAPIKey,
    UserNotFoundError,
    ApiKeyDisabledError,
    ApiKeyNotFoundError,
    InsufficientPermission,
    InvalidPermissionError,
)
from src.management.api_keys.permissions import (
    clearPermissions,
    registerPermissions,
)


class _DummySessionManager:
    def __init__(self):
        self.session = Mock()
        self.session.commit = AsyncMock()

    @asynccontextmanager
    async def get_session(self):
        yield self.session


class TestApiKeyService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        clearPermissions()
        registerPermissions(["chat.run", "chat.read"])
        self.created_at = datetime(2026, 3, 28, 13, 0, 0)
        self.session_manager = _DummySessionManager()
        self.api_key_repo = Mock()
        self.project_repo = Mock()
        self.service = ApiKeyService(
            config={"key_secret": "secret", "api_key_secret_length": 8},
            logger=Mock(),
            api_key_repo=self.api_key_repo,
            project_repo=self.project_repo,
            session_manager=self.session_manager,
        )

    async def test_create_api_key_returns_created_resource_with_raw_key(self):
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        created = SimpleNamespace(
            id=11,
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
        self.assertEqual(result.unwrap().project_id, "proj-1")
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
        self.assertEqual(result.unwrap().results[0].project_id, "proj-1")

    async def test_get_api_keys_returns_project_not_found(self):
        self.project_repo.getByUuid = AsyncMock(return_value=None)

        result = await self.service.getApiKeys(project_uuid="proj-404")

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_get_api_key_by_id_returns_project_scoped_response(self):
        api_key = SimpleNamespace(
            id=11,
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.getApiKey(11)

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap().project_id, "proj-1")

    async def test_get_api_key_returns_not_found_from_lookup(self):
        self.api_key_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKey(11)

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_get_api_key_returns_project_not_found_when_owner_project_missing(
        self,
    ):
        api_key = SimpleNamespace(
            id=11,
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKey(11)

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_update_api_key_rejects_missing_key(self):
        self.api_key_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_id=11,
            name="updated",
            description="desc",
            permissions=["chat.run"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_update_api_key_rejects_unknown_permissions(self):
        result = await self.service.updateApiKey(
            api_key_id=11,
            name="updated",
            description="desc",
            permissions=["unknown.permission"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidPermissionError)

    async def test_update_api_key_returns_updated_response(self):
        current = SimpleNamespace(
            id=11,
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
            project_id=7,
            name="updated",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.read"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByKey = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.updateApiKey(
            api_key_id=11,
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
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByKey = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_id=11,
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
            project_id=7,
            name="updated",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.read"],
            disabled=False,
        )
        self.api_key_repo.getByKey = AsyncMock(return_value=current)
        self.api_key_repo.updateById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.updateApiKey(
            api_key_id=11,
            name="updated",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_delete_api_key_returns_not_found_for_missing_key(self):
        self.api_key_repo.deleteById = AsyncMock(return_value=False)

        result = await self.service.deleteApiKey(11)

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_delete_api_key_commits_on_success(self):
        self.api_key_repo.deleteById = AsyncMock(return_value=True)

        result = await self.service.deleteApiKey(11)

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertTrue(result.unwrap())
        self.session_manager.session.commit.assert_awaited_once()

    async def test_set_api_key_disabled_returns_updated_response(self):
        current = SimpleNamespace(
            id=11,
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
            project_id=7,
            name="current",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=True,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByKey = AsyncMock(return_value=current)
        self.api_key_repo.updateDisabledById = AsyncMock(return_value=updated)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.setApiKeyDisabled(
            api_key_id=11, disabled=True
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertTrue(result.unwrap().disabled)
        self.session_manager.session.commit.assert_awaited_once()

    async def test_verify_api_key_returns_runtime_context(self):
        api_key = SimpleNamespace(
            id=11,
            user_id="u1",
            project_id=7,
            permissions=["chat.run", "chat.read"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap()["org_id"], "org-1")
        self.assertEqual(result.unwrap()["project_uid"], "proj-1")

    async def test_verify_api_key_requires_at_least_one_permission(self):
        with self.assertRaises(ValueError):
            await self.service.verifyApiKey("sk_demo.secret", [])

    async def test_verify_api_key_rejects_unknown_key(self):
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=None)

        result = await self.service.verifyApiKey(
            "sk_missing.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InvalidAPIKey)

    async def test_verify_api_key_rejects_disabled_key(self):
        api_key = SimpleNamespace(
            id=11,
            user_id="u1",
            project_id=7,
            permissions=["chat.run", "chat.read"],
            disabled=True,
        )
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=api_key)

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyDisabledError)

    async def test_verify_api_key_rejects_missing_user_id(self):
        api_key = SimpleNamespace(
            id=11,
            user_id=None,
            project_id=7,
            permissions=["chat.read"],
            disabled=False,
        )
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=api_key)

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), UserNotFoundError)

    async def test_verify_api_key_rejects_missing_permission(self):
        api_key = SimpleNamespace(
            id=11,
            user_id="u1",
            project_id=7,
            permissions=["chat.run"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), InsufficientPermission)

    async def test_verify_api_key_returns_project_not_found(self):
        api_key = SimpleNamespace(
            id=11,
            user_id="u1",
            project_id=7,
            permissions=["chat.run", "chat.read"],
            disabled=False,
        )
        self.api_key_repo.getByHashedKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.verifyApiKey(
            "sk_demo.secret", ["chat.read"]
        )

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ProjectNotFoundError)

    async def test_get_api_key_project_id_returns_project_uuid(self):
        api_key = SimpleNamespace(
            id=11,
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        project = SimpleNamespace(id=7, organization_id="org-1", uuid="proj-1")
        self.api_key_repo.getByKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=project)

        result = await self.service.getApiKeyProjectId(11)

        self.assertEqual(result.status, ResultStatus.Ok)
        self.assertEqual(result.unwrap(), "proj-1")

    async def test_get_api_key_project_id_returns_not_found_from_lookup(self):
        self.api_key_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKeyProjectId(11)

        self.assertEqual(result.status, ResultStatus.Err)
        self.assertIsInstance(result.err(), ApiKeyNotFoundError)

    async def test_get_api_key_project_id_returns_project_not_found(self):
        api_key = SimpleNamespace(
            id=11,
            project_id=7,
            name="k1",
            description="desc",
            hint="hint",
            created_at=self.created_at,
            permissions=["chat.run"],
            disabled=False,
        )
        self.api_key_repo.getByKey = AsyncMock(return_value=api_key)
        self.project_repo.getByKey = AsyncMock(return_value=None)

        result = await self.service.getApiKeyProjectId(11)

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
        self.assertEqual(result.results, ["chat.read", "chat.run"])

    async def test_audit_permissions_returns_stale_and_unused_permissions(self):
        self.api_key_repo.listDistinctPermissions = AsyncMock(
            return_value=["chat.run", "orphan.permission"]
        )

        result = await self.service.auditPermissions()

        self.assertEqual(
            result.registered_permissions, ["chat.read", "chat.run"]
        )
        self.assertEqual(
            result.stored_permissions, ["chat.run", "orphan.permission"]
        )
        self.assertEqual(result.stale_permissions, ["orphan.permission"])
        self.assertEqual(result.unused_permissions, ["chat.read"])
