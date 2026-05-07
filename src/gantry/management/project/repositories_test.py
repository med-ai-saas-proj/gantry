import os
import inspect
import unittest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock

from pyrusult import Ok, Err


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from gantry.db.repositories import CacheRepository
from gantry.management.project.repositories import ProjectSettingsRepository


class _CacheSpy(CacheRepository):
    def __init__(self, cached=None):
        super().__init__()
        self.cached = cached
        self.get_keys: list[str] = []
        self.set_items: list[tuple[str, object]] = []
        self.invalidated_keys: list[str] = []

    async def getCached(self, key: str):
        self.get_keys.append(key)
        return Ok(self.cached) if self.cached is not None else Err(None)

    async def setCache(self, key: str, value):
        self.set_items.append((key, value))
        self.cached = value

    async def invalidateCached(self, key: str):
        self.invalidated_keys.append(key)
        self.cached = None

    async def getCachedOrCall(self, key: str, fn, *args, **kwargs):
        self.get_keys.append(key)
        if self.cached is not None:
            return self.cached
        res = fn(*args, **kwargs)
        if inspect.iscoroutine(res):
            res = await res
        self.set_items.append((key, res))
        self.cached = res
        return res


class TestProjectSettingsRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = ProjectSettingsRepository(_CacheSpy())
        self.session = Mock()

    async def test_get_or_create_uses_on_conflict_returning(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = "settings"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getOrCreate(self.session, 7)

        self.assertEqual(result, "settings")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("ON CONFLICT", str(stmt))
        self.assertIn("RETURNING", str(stmt))
        self.assertIn("project_id", str(stmt))

    async def test_get_or_create_by_uuid_cache_hit_skips_db(self):
        project_uuid = str(uuid4())
        cache_repo = _CacheSpy(cached="cached-settings")
        repo = ProjectSettingsRepository(cache_repo)
        session = Mock()
        session.execute = AsyncMock()

        result = await repo.getOrCreateByUuid(session, project_uuid)

        self.assertEqual(result, "cached-settings")
        self.assertEqual(
            cache_repo.get_keys,
            [ProjectSettingsRepository.getCacheKey(project_uuid)],
        )
        session.execute.assert_not_awaited()

    async def test_get_or_create_by_uuid_cache_miss_existing_row_caches_select_result(
        self,
    ):
        project_uuid = str(uuid4())
        cache_repo = _CacheSpy()
        repo = ProjectSettingsRepository(cache_repo)
        session = Mock()
        select_res = Mock()
        select_res.scalar_one_or_none.return_value = "db-settings"
        session.execute = AsyncMock(return_value=select_res)

        result = await repo.getOrCreateByUuid(session, project_uuid)

        self.assertEqual(result, "db-settings")
        session.execute.assert_awaited_once()
        self.assertEqual(
            cache_repo.get_keys,
            [ProjectSettingsRepository.getCacheKey(project_uuid)],
        )
        self.assertEqual(len(cache_repo.set_items), 1)
        self.assertEqual(
            cache_repo.set_items[0][0],
            ProjectSettingsRepository.getCacheKey(project_uuid),
        )
        self.assertEqual(cache_repo.set_items[0][1], "db-settings")

    async def test_get_or_create_by_uuid_missing_row_inserts_and_overwrites_cache(
        self,
    ):
        project_uuid = str(uuid4())
        cache_repo = _CacheSpy()
        repo = ProjectSettingsRepository(cache_repo)
        session = Mock()
        select_res = Mock()
        select_res.scalar_one_or_none.return_value = None
        insert_res = Mock()
        insert_res.scalar_one.return_value = "inserted-settings"
        session.execute = AsyncMock(side_effect=[select_res, insert_res])

        result = await repo.getOrCreateByUuid(session, project_uuid)

        self.assertEqual(result, "inserted-settings")
        self.assertEqual(session.execute.await_count, 2)
        self.assertEqual(len(cache_repo.set_items), 2)
        self.assertIsNone(cache_repo.set_items[0][1])
        self.assertEqual(
            cache_repo.set_items[1],
            (
                ProjectSettingsRepository.getCacheKey(project_uuid),
                "inserted-settings",
            ),
        )

    async def test_upsert_updates_rate_limit_spending_limit_and_extra(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = "settings"
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.upsert(
            self.session,
            7,
            150,
            8000,
            {"mode": "burst"},
        )

        self.assertEqual(result, "settings")
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("ON CONFLICT", str(stmt))
        self.assertIn("spending_limit", str(stmt))
        self.assertIn("rate_limit", str(stmt))
        self.assertIn("RETURNING", str(stmt))
