from gantry.service.file_storage.models import FileStatus
from gantry.service.file_storage.repositories import FileRepository

import unittest
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock


class TestFileRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = FileRepository()
        self.session = Mock()

    async def test_get_available_ids_by_uuids_filters_project_and_status(self):
        file_uuid = uuid4()
        execute_res = Mock()
        execute_res.scalars.return_value.all.return_value = ["file-row"]
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getAvailableIdsByUUIDs(
            self.session,
            [file_uuid],
            project_id=17,
        )

        self.assertEqual(result, ["file-row"])
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("project_id", str(stmt))
        self.assertIn("status", str(stmt))

    async def test_get_available_ids_by_metadata_applies_filters(self):
        execute_res = Mock()
        execute_res.scalars.return_value.all.return_value = ["file-row"]
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getAvailableIdsByMetadata(
            self.session,
            {"kind": "xray", "pages": 3},
            project_id=17,
        )

        self.assertEqual(result, ["file-row"])
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("extra_metadata", str(stmt))
        self.assertIn("project_id", str(stmt))

    async def test_get_available_by_ids_returns_matching_rows(self):
        execute_res = Mock()
        execute_res.scalars.return_value.all.return_value = ["file-row"]
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.getAvailableByIds(self.session, [1, 2])

        self.assertEqual(result, ["file-row"])
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("status", str(stmt))

    async def test_get_available_by_uuid_uses_limit_and_project_scope(self):
        file_uuid = uuid4()
        self.repo.selectOne = AsyncMock(return_value="file-row")

        result = await self.repo.getAvailableByUUID(
            self.session,
            file_uuid,
            project_id=17,
        )

        self.assertEqual(result, "file-row")
        stmt = self.repo.selectOne.await_args.args[1]  # type: ignore
        self.assertIn("LIMIT", str(stmt))
        self.assertIn("project_id", str(stmt))

    async def test_get_file_list_by_project_id_delegates_to_select_many(self):
        self.repo.selectMany = AsyncMock(return_value=["file-row"])

        result = await self.repo.getFileListByProjectID(self.session, 17)

        self.assertEqual(result, ["file-row"])
        stmt = self.repo.selectMany.await_args.args[1]  # type: ignore
        self.assertIn("status", str(stmt))

    async def test_delete_file_by_id_returns_deleted_row(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = SimpleNamespace(id=5)
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.deleteFileById(self.session, 5)

        self.assertEqual(result.id, 5)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("DELETE", str(stmt))
        self.assertIn("status", str(stmt))

    async def test_mark_file_as_available_by_id_returns_row(self):
        execute_res = Mock()
        execute_res.scalar_one.return_value = SimpleNamespace(id=5)
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.markFileAsAvailableById(self.session, 5)

        self.assertEqual(result.id, 5)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("UPDATE", str(stmt))
        self.assertIn("status", str(stmt))

    async def test_mark_file_as_deleted_by_uuid_returns_none_when_missing(self):
        file_uuid = uuid4()
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.markFileAsDeletedByUUID(
            self.session,
            file_uuid,
            project_id=17,
        )

        self.assertIsNone(result)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("UPDATE", str(stmt))
        self.assertIn("status", str(stmt))

    async def test_update_extra_metadata_by_uuid_returns_updated_row(self):
        file_uuid = uuid4()
        execute_res = Mock()
        execute_res.scalar_one_or_none.return_value = SimpleNamespace(id=9)
        self.session.execute = AsyncMock(return_value=execute_res)

        result = await self.repo.updateExtraMetadataByUUID(
            self.session,
            file_uuid,
            project_id=17,
            extra_metadata={"kind": "xray"},
        )

        assert result is not None
        self.assertEqual(result.id, 9)
        stmt = self.session.execute.await_args.args[0]
        self.assertIn("extra_metadata", str(stmt))
