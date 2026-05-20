import os
import json
import unittest
from uuid import UUID, uuid4
from types import SimpleNamespace
from typing import cast
from datetime import datetime
from unittest.mock import ANY, Mock, AsyncMock, patch


os.environ.setdefault("GANTRY_SERVER__CONFIG_FILE", "gantry.toml")

from gantry.db.session import AsyncSessionManager
from gantry.service.file_storage.models import FileStatus
from gantry.service.file_storage.services import (
    FileStorageService,
    FileNotFoundInSystemError,
)
from gantry.service.file_storage.settings import ObjectStorageSettings

from pyrusult import Ok, ResultStatus


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionManager:
    def __init__(self, session):
        self._session = session

    def get_session(self):
        return _SessionContext(self._session)


def _make_settings():
    return ObjectStorageSettings(
        s3_bucket_name="bucket",
        s3_region_name="region",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
        s3_endpoint_url="http://localhost:9000",
        s3_presigned_url_expiry_seconds=120,
        redis_cache_expiry_seconds=45,
    )


def _make_service(
    *, file_repo=None, redis=None, project_repo=None, storage=None, session=None
):
    session = session or Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    file_repo = file_repo or Mock()
    if redis is None:
        redis = Mock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        redis.delete = AsyncMock()
    project_repo = project_repo or Mock()
    storage = storage or Mock()
    settings = _make_settings()
    return (
        FileStorageService(
            storage,
            cast(AsyncSessionManager, _SessionManager(session)),
            settings,
            file_repo,
            redis,
            project_repo,
        ),
        session,
        file_repo,
        redis,
        project_repo,
        storage,
        settings,
    )


class TestFileStorageService(unittest.IsolatedAsyncioTestCase):
    async def test_create_bucket_if_not_exists_creates_missing_bucket(self):
        service, *_ = _make_service()

        class _NoSuchBucket(Exception):
            pass

        service.storage_backend.exceptions = SimpleNamespace(  # type: ignore
            NoSuchBucket=_NoSuchBucket
        )
        service.storage_backend.head_bucket.side_effect = _NoSuchBucket()  # type: ignore
        service.storage_backend.create_bucket = Mock()

        service.create_bucket_if_not_exists()

        service.storage_backend.create_bucket.assert_called_once()

    async def test_upload_file_persists_then_marks_available(self):
        file_uid = uuid4()
        service, session, file_repo, _, _, storage, _ = _make_service()
        uploaded = {}

        def add_side_effect(obj):
            uploaded["file"] = obj

        session.add.side_effect = add_side_effect

        async def flush_side_effect():
            uploaded["file"].id = 99

        session.flush = AsyncMock(side_effect=flush_side_effect)
        storage.put_object = Mock()
        file_repo.markFileAsAvailableById = AsyncMock(
            return_value=SimpleNamespace(id=99)
        )

        with (
            patch(
                "gantry.service.file_storage.services.uuid7",
                return_value=file_uid,
            ),
            patch(
                "gantry.service.file_storage.services.asyncio.to_thread",
                new=AsyncMock(side_effect=lambda fn, *args: fn(*args)),
            ),
        ):
            result = await service.uploadFile(
                file_name="report.pdf",
                file_data=b"abc",
                file_size=3,
                mime_type="application/pdf",
                project_id=7,
                ext="pdf",
            )

        self.assertEqual(result, file_uid)
        self.assertEqual(uploaded["file"].filepath, f"uploads/{file_uid}.pdf")
        session.add.assert_called_once()
        session.commit.assert_awaited()
        storage.put_object.assert_called_once()
        file_repo.markFileAsAvailableById.assert_awaited_once_with(session, 99)

    async def test_upload_file_by_project_uuid_looks_up_project_and_delegates(
        self,
    ):
        project_uid = uuid4()
        service, _, _, _, project_repo, _, _ = _make_service()
        project_repo.getByUuid = AsyncMock(
            return_value=SimpleNamespace(id=17, uuid=project_uid)
        )
        service.uploadFile = AsyncMock(return_value=uuid4())

        result = await service.uploadFileByProjectUUID(
            file_name="a.txt",
            file_data=b"a",
            file_size=1,
            mime_type="text/plain",
            project_uid=project_uid,
            ext=None,
        )

        self.assertIsInstance(result, UUID)
        project_repo.getByUuid.assert_awaited_once_with(ANY, str(project_uid))
        service.uploadFile.assert_awaited_once()

    async def test_get_file_info_uses_cache_hit(self):
        file_uid = uuid4()
        cached_at = datetime(2026, 1, 1, 12, 0, 0)
        cached = {
            "id": 5,
            "uid": str(file_uid),
            "filename": "doc.txt",
            "storage_path": "/uploads/doc.txt",
            "mime_type": "text/plain",
            "size": 11,
            "created_at": cached_at.isoformat(),
            "extra_metadata": {"kind": "note"},
        }
        file_repo = Mock()
        file_repo.getAvailableByUUID = AsyncMock()
        redis = Mock()
        redis.get = AsyncMock(return_value=json.dumps(cached))
        service, _, _, _, _, _, _ = _make_service(
            redis=redis, file_repo=file_repo
        )

        result = await service.getFileInfo(file_uid, 7)

        if result.status != ResultStatus.Ok:
            self.fail(
                f"Expected Ok but got {result.status}: {result.err() if result.status == ResultStatus.Err else ''}"
            )
        self.assertEqual(result.unwrap()["filename"], "doc.txt")
        file_repo.getAvailableByUUID.assert_not_awaited()

    async def test_get_file_info_cache_miss_loads_and_caches(self):
        file_uid = uuid4()
        file_record = SimpleNamespace(
            id=8,
            uuid=file_uid,
            original_filename="doc.txt",
            filepath="/uploads/doc.txt",
            mime_type="text/plain",
            size_in_bytes=11,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            extra_metadata={"kind": "note"},
            status=FileStatus.AVAILABLE,
        )
        file_repo = Mock()
        file_repo.getAvailableByUUID = AsyncMock(return_value=file_record)
        service, session, _, redis, _, _, settings = _make_service(
            file_repo=file_repo
        )

        result = await service.getFileInfo(file_uid, 7)

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap()["id"], 8)
        redis.set.assert_awaited_once()
        self.assertEqual(
            redis.set.await_args.kwargs["ex"],
            settings.redis_cache_expiry_seconds,
        )
        session.commit.assert_not_awaited()

    async def test_get_file_url_returns_presigned_url(self):
        file_uid = uuid4()
        service, *_ = _make_service()
        service.getFileInfo = AsyncMock(
            return_value=Ok(
                {
                    "id": 1,
                    "uid": file_uid,
                    "filename": "doc.txt",
                    "storage_path": "/uploads/doc.txt",
                    "mime_type": "text/plain",
                    "size": 11,
                    "created_at": datetime(2026, 1, 1, 12, 0, 0),
                    "extra_metadata": None,
                }
            )
        )
        service.storage_backend.generate_presigned_url = Mock(
            return_value="http://signed"
        )

        result = await service.getFileUrl(file_uid, 7)

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(result.unwrap(), "http://signed")

    async def test_update_file_metadata_invalidates_cache(self):
        file_uid = uuid4()
        service, session, file_repo, redis, _, _, _ = _make_service()
        file_repo.updateExtraMetadataByUUID = AsyncMock(
            return_value=SimpleNamespace(id=5)
        )

        result = await service.updateFileMetadata(file_uid, 7, {"kind": "note"})

        self.assertTrue(result.status == ResultStatus.Ok)
        session.commit.assert_awaited_once()
        redis.delete.assert_awaited_once_with(
            FileStorageService._cache_key(7, file_uid)
        )

    async def test_update_file_metadata_missing_file_returns_error(self):
        file_uid = uuid4()
        service, session, file_repo, redis, _, _, _ = _make_service()
        file_repo.updateExtraMetadataByUUID = AsyncMock(return_value=None)

        result = await service.updateFileMetadata(file_uid, 7, None)

        self.assertTrue(result.status == ResultStatus.Err)
        self.assertIsInstance(result.err(), FileNotFoundInSystemError)
        session.commit.assert_not_awaited()
        redis.delete.assert_not_awaited()

    async def test_delete_file_removes_from_storage_and_db(self):
        file_uid = uuid4()
        file_record = SimpleNamespace(id=5, filepath="/uploads/doc.txt")
        service, session, file_repo, redis, _, storage, _ = _make_service()
        file_repo.markFileAsDeletedByUUID = AsyncMock(return_value=file_record)
        file_repo.deleteFileById = AsyncMock(return_value=file_record)
        storage.delete_object = Mock()

        with patch(
            "gantry.service.file_storage.services.asyncio.to_thread",
            new=AsyncMock(side_effect=lambda fn, *args: fn(*args)),
        ):
            result = await service.deleteFile(file_uid, 7)

        self.assertTrue(result.status == ResultStatus.Ok)
        self.assertEqual(session.commit.await_count, 2)
        redis.delete.assert_awaited_once_with(
            FileStorageService._cache_key(7, file_uid)
        )
        storage.delete_object.assert_called_once()
        file_repo.deleteFileById.assert_awaited_once_with(session, 5)

    async def test_delete_file_by_project_uuid_looks_up_project(self):
        project_uid = uuid4()
        service, _, _, _, project_repo, _, _ = _make_service()
        project_repo.getByUuid = AsyncMock(
            return_value=SimpleNamespace(id=17, uuid=project_uid)
        )
        service.deleteFile = AsyncMock(return_value=Ok(None))

        result = await service.deleteFileByProjectUUID(uuid4(), project_uid)

        self.assertTrue(result.status == ResultStatus.Ok)
        service.deleteFile.assert_awaited_once()

    async def test_list_files_in_project_maps_rows(self):
        service, session, file_repo, _, _, _, _ = _make_service()
        file_repo.getFileListByProjectID = AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=5,
                    uuid=uuid4(),
                    original_filename="doc.txt",
                    filepath="/uploads/doc.txt",
                    mime_type="text/plain",
                    size_in_bytes=11,
                    created_at=datetime(2026, 1, 1, 12, 0, 0),
                    extra_metadata=None,
                )
            ]
        )

        result = await service.listFilesInProject(7)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "doc.txt")
        file_repo.getFileListByProjectID.assert_awaited_once_with(session, 7)
