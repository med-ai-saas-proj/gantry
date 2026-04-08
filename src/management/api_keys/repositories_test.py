import os
import unittest
from unittest.mock import Mock, AsyncMock, patch


os.environ.setdefault("KEYCLOAK_SERVICE_CLIENT_SECRET", "test-secret")

from src.management.api_keys.repositories import ApiKeyRepository


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
        self.assertEqual(result["organization_uuid"], "org-1")
        self.assertEqual(result["rpm_limit_organization"], 10)
        self.assertEqual(result["rpm_limit_project"], 55)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("JOIN", str(stmt))
        self.assertIn("organization_id", str(stmt))

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
