import os
import unittest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.db.repositories import CacheRepository
from gantry.management.api_key.repositories import ApiKeyRepository


class _CacheSpy(CacheRepository):
    def __init__(self, cached=None):
        super().__init__()
        self.cached = cached
        self.get_keys: list[str] = []
        self.set_items: list[tuple[str, object]] = []
        self.invalidated_keys: list[str] = []

    async def getCache(self, key: str):
        self.get_keys.append(key)
        return self.cached

    async def setCache(self, key: str, value):
        self.set_items.append((key, value))
        self.cached = value

    async def invalidateCache(self, key: str):
        self.invalidated_keys.append(key)
        self.cached = None


class TestApiKeyRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = ApiKeyRepository()
        self.session = Mock()

    async def test_get_by_hashed_key_builds_lookup_statement(self):
        with patch.object(
            self.repo, "selectOne", AsyncMock(return_value="api-key")
        ) as select_one:
            result = await self.repo.getByHashedKey(self.session, "hashed")

        self.assertEqual(result, "api-key")
        stmt = select_one.await_args.args[1]
        self.assertIn(".hashed_key", str(stmt))
        self.assertIn("LIMIT", str(stmt))

    async def test_get_by_project_id_builds_sorted_query(self):
        with patch.object(
            self.repo, "selectMany", AsyncMock(return_value=["one", "two"])
        ) as select_many:
            result = await self.repo.getByProjectId(self.session, 7)

        self.assertEqual(result, ["one", "two"])
        stmt = select_many.await_args.args[1]
        self.assertIn(".project_id", str(stmt))
        self.assertIn("ORDER BY", str(stmt))

    async def test_get_context_by_hashed_key_builds_joined_lookup(self):
        execute_res = Mock()
        execute_res.mappings.return_value.first.return_value = {
            "api_key_id": 11,
            "api_key_uuid": "api-key-uuid",
            "user_id": "u1",
            "project_id": 7,
            "hashed_key": "hashed",
            "permissions": ["chat.run"],
            "disabled": False,
            "project_uuid": "proj-1",
            "organization_uuid": "org-1",
            "organization_rate_limit": 10,
            "project_rate_limit": 55,
        }
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getContextByHashedKey(self.session, "hashed")

        self.assertIsNotNone(result)
        self.assertEqual(result["api_key_uuid"], "api-key-uuid")
        self.assertEqual(result["org_id"], "org-1")
        self.assertEqual(result["organization_uuid"], "org-1")
        self.assertEqual(result["rpm_limit_organization"], 10)
        self.assertEqual(result["rpm_limit_project"], 55)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("JOIN", str(stmt))
        self.assertIn("organization_id", str(stmt))

    async def test_get_context_by_hashed_key_cache_hit_skips_db(self):
        cached = {
            "api_key_id": 11,
            "api_key_uuid": "api-key-uuid",
            "user_uuid": "u1",
            "project_id": 7,
            "org_id": "org-1",
            "organization_uuid": "org-1",
            "project_uuid": "proj-1",
            "hashed_key": "hashed",
            "permissions": ["chat.run"],
            "disabled": False,
            "rpm_limit_organization": 10,
            "rpm_limit_project": 55,
            "spending_limit_organization": 1234,
            "spending_limit_project": 5678,
        }
        cache_repo = _CacheSpy(cached=cached)
        repo = ApiKeyRepository(cache_repo)
        session = Mock()
        session.execute = AsyncMock()

        result = await repo.getContextByHashedKey(session, "hashed")

        self.assertEqual(result, cached)
        self.assertEqual(
            cache_repo.get_keys, ["api_keys:context_record:hashed"]
        )
        session.execute.assert_not_awaited()

    async def test_get_context_by_hashed_key_cache_miss_queries_and_caches(
        self,
    ):
        cache_repo = _CacheSpy()
        repo = ApiKeyRepository(cache_repo)
        session = Mock()
        execute_res = Mock()
        execute_res.mappings.return_value.first.return_value = {
            "api_key_id": 11,
            "api_key_uuid": "api-key-uuid",
            "user_id": "u1",
            "project_id": 7,
            "hashed_key": "hashed",
            "permissions": ["chat.run"],
            "disabled": False,
            "project_uuid": "proj-1",
            "organization_uuid": "org-1",
            "organization_rate_limit": 10,
            "project_rate_limit": 55,
            "organization_spending_limit": 1234,
            "project_spending_limit": 5678,
        }
        session.execute = AsyncMock(return_value=execute_res)

        result = await repo.getContextByHashedKey(session, "hashed")

        self.assertEqual(result["spending_limit_organization"], 1234)
        self.assertEqual(result["spending_limit_project"], 5678)
        session.execute.assert_awaited_once()
        self.assertEqual(len(cache_repo.set_items), 1)
        self.assertEqual(
            cache_repo.set_items[0][0], "api_keys:context_record:hashed"
        )

    async def test_count_by_project_id_returns_scalar_count(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = 3
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.countByProjectId(self.session, 7)

        self.assertEqual(result, 3)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("count", str(stmt).lower())

    async def test_count_by_project_id_coerces_null_to_zero(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = None
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.countByProjectId(self.session, 7)

        self.assertEqual(result, 0)

    async def test_create_returns_inserted_entity(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = "created"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.create(
            self.session,
            uuid=uuid4(),
            user_id="u1",
            project_id=7,
            hashed_key="hashed",
            hint="hint",
            name="name",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result, "created")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("INSERT INTO", str(stmt))
        self.assertIn("RETURNING", str(stmt))

    async def test_update_by_id_returns_updated_entity_or_none(self):
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = "updated"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.updateById(
            self.session,
            11,
            name="name",
            description="desc",
            permissions=["chat.read"],
        )

        self.assertEqual(result, "updated")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("UPDATE", str(stmt))
        self.assertIn("RETURNING", str(stmt))

        execute_res.scalar_one_or_none.return_value = None
        result_none = await self.repo.updateById(
            self.session,
            11,
            name="name",
            description="desc",
            permissions=["chat.read"],
        )
        self.assertIsNone(result_none)

    async def test_update_disabled_by_id_returns_updated_entity_or_none(self):
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = "updated"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.updateDisabledById(
            self.session,
            11,
            disabled=True,
        )

        self.assertEqual(result, "updated")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("UPDATE", str(stmt))
        self.assertIn("disabled", str(stmt))

        execute_res.scalar_one_or_none.return_value = None
        result_none = await self.repo.updateDisabledById(
            self.session,
            11,
            disabled=False,
        )
        self.assertIsNone(result_none)

    async def test_delete_by_id_returns_bool(self):
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = 11
        self.session.execute = AsyncMock(return_value=execute_res)

        deleted = await self.repo.deleteById(self.session, 11)
        self.assertTrue(deleted)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("DELETE FROM", str(stmt))

        execute_res.scalar_one_or_none.return_value = None
        not_deleted = await self.repo.deleteById(self.session, 11)
        self.assertFalse(not_deleted)

    async def test_list_distinct_permissions_returns_sorted_non_empty_entries(
        self,
    ):
        execute_res = Mock()
        scalars_res = Mock()
        scalars_res.all.return_value = ["file.read", "", None, "chat.run"]
        execute_res.scalars.return_value = scalars_res
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.listDistinctPermissions(self.session)

        self.assertEqual(result, ["file.read", "chat.run"])
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("unnest", str(stmt).lower())
