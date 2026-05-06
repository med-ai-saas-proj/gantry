import os
import unittest
from unittest.mock import Mock, AsyncMock


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.db.repositories import CacheRepository
from gantry.management.organization.repositories import OrgSettingsRepository


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


class TestOrgSettingsRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = OrgSettingsRepository()
        self.session = Mock()

    async def test_get_or_create_uses_on_conflict_returning(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = "settings"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getOrCreate(self.session, "org-1")

        self.assertEqual(result, "settings")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("ON CONFLICT", str(stmt))
        self.assertIn("RETURNING", str(stmt))
        self.assertIn("org_id", str(stmt))

    async def test_get_or_create_cache_hit_skips_db(self):
        cache_repo = _CacheSpy(cached="cached-settings")
        repo = OrgSettingsRepository(cache_repo)
        session = Mock()
        session.execute = AsyncMock()

        result = await repo.getOrCreate(session, "org-1")

        self.assertEqual(result, "cached-settings")
        self.assertEqual(cache_repo.get_keys, ["org:settings:org-1"])
        session.execute.assert_not_awaited()

    async def test_get_or_create_cache_miss_queries_and_sets_cache(self):
        cache_repo = _CacheSpy()
        repo = OrgSettingsRepository(cache_repo)
        session = Mock()
        execute_res = Mock()
        execute_res.scalar_one.return_value = "db-settings"
        session.execute = AsyncMock(return_value=execute_res)

        result = await repo.getOrCreate(session, "org-1")

        self.assertEqual(result, "db-settings")
        session.execute.assert_awaited_once()
        self.assertEqual(cache_repo.get_keys, ["org:settings:org-1"])
        self.assertEqual(
            cache_repo.set_items, [("org:settings:org-1", "db-settings")]
        )

    async def test_upsert_updates_rate_limit_spending_limit_and_extra(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = "settings"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.upsert(
            self.session,
            "org-1",
            100,
            5000,
            {"theme": "dark"},
        )

        self.assertEqual(result, "settings")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("ON CONFLICT", str(stmt))
        self.assertIn("spending_limit", str(stmt))
        self.assertIn("rate_limit", str(stmt))
        self.assertIn("RETURNING", str(stmt))

    async def test_upsert_sets_cache_with_fresh_settings(self):
        cache_repo = _CacheSpy()
        repo = OrgSettingsRepository(cache_repo)
        session = Mock()
        execute_res = Mock()
        execute_res.scalar_one.return_value = "settings"
        session.execute = AsyncMock(return_value=execute_res)

        result = await repo.upsert(
            session,
            "org-1",
            100,
            5000,
            {"theme": "dark"},
        )

        self.assertEqual(result, "settings")
        self.assertEqual(
            cache_repo.set_items, [("org:settings:org-1", "settings")]
        )

    async def test_delete_by_org_id_invalidates_cache(self):
        cache_repo = _CacheSpy(cached="settings")
        repo = OrgSettingsRepository(cache_repo)
        session = Mock()
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = "org-1"
        session.execute = AsyncMock(return_value=execute_res)

        deleted = await repo.deleteByOrgId(session, "org-1")

        self.assertTrue(deleted)
        self.assertEqual(cache_repo.invalidated_keys, ["org:settings:org-1"])
