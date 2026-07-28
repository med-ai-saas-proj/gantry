from pyrusult import Ok, Err, Result, ResultStatus
from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.json_utils import json_serializer
from gantry.shared.utils.uuid_utils import uuid7
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
)

from .types import FileRecord
from .models import File, FileStatus
from .settings import ObjectStorageSettings
from .repositories import FileRepository

import json
import uuid
import asyncio
from typing import TYPE_CHECKING, BinaryIO
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, and_, select
from redis.asyncio import Redis


class FileNotFoundInSystemError(RecoverableError):
    status = 404
    code = "file_not_found"
    title = "File not found"
    detail = "The requested file was not found in storage."

    def __init__(
        self,
        message: str | None = None,
        from_exception: Exception | None = None,
    ):
        super().__init__(from_exception=from_exception)
        self.message = message


if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class FileStorageService:
    if TYPE_CHECKING:

        def __init__(
            self,
            storage_backend: S3Client,
            session_manager: AsyncSessionManager,
            file_storage_settings: ObjectStorageSettings,
            file_repo: FileRepository,
            redis: Redis,
        ):
            self.storage_backend = storage_backend
            self.session_manager = session_manager
            self.file_storage_settings = file_storage_settings
            self.file_repo = file_repo
            self.redis = redis
    else:

        def __init__(
            self,
            storage_backend,
            session_manager: AsyncSessionManager,
            file_storage_settings: ObjectStorageSettings,
            file_repo: FileRepository,
            redis: Redis,
        ):
            self.storage_backend = storage_backend
            self.session_manager = session_manager
            self.file_storage_settings = file_storage_settings
            self.file_repo = file_repo
            self.redis = redis

    def create_bucket_if_not_exists(self):
        """Create the S3 bucket if it doesn't exist."""
        try:
            self.storage_backend.head_bucket(
                Bucket=self.file_storage_settings.s3_bucket_name
            )
        except self.storage_backend.exceptions.NoSuchBucket:
            self.storage_backend.create_bucket(
                Bucket=self.file_storage_settings.s3_bucket_name,
                CreateBucketConfiguration={
                    "LocationConstraint": self.file_storage_settings.s3_region_name  # type: ignore
                },
            )

    def _uploadFileToStorage(
        self,
        file_name: str,
        file_size: int,
        file_object: BinaryIO | bytes,
        mime_type: str = "application/octet-stream",
    ) -> None:
        """Upload a file to the storage backend."""
        self.storage_backend.put_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_name,
            Body=file_object,
            ContentLength=file_size,
            ContentType=mime_type,
        )

    async def uploadFile(
        self,
        file_name: str,
        file_data: BinaryIO | bytes,
        file_size: int,
        mime_type: str,
        project_id: int,
        ext: str | None = None,
        file_uid: uuid.UUID | None = None,
        extra_metadata: dict | None = None,
    ):
        """Upload a file and store its metadata."""
        if file_uid is None:
            file_uid = uuid7()
        file_path = (
            f"uploads/{file_uid}.{ext}" if ext else f"/uploads/{file_uid}"
        )
        async with self.session_manager.get_session() as session:
            file_record = File(
                project_id=project_id,
                uuid=file_uid,
                original_filename=file_name,
                filepath=file_path,
                mime_type=mime_type,
                size_in_bytes=file_size,
                extra_metadata=extra_metadata,
            )
            session.add(file_record)
            await session.flush()
            file_id = file_record.id
            await session.commit()

        await asyncio.to_thread(
            self._uploadFileToStorage,
            file_path,
            file_size,
            file_data,
            mime_type,
        )
        async with self.session_manager.get_session() as session:
            await self.file_repo.markFileAsAvailableById(session, file_id)
            await session.commit()
        return file_uid

    def _loadFileContentFromStorage(
        self,
        file_path: str,
    ):
        res = self.storage_backend.get_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_path,
        )
        return res["Body"].read()

    @staticmethod
    def _cache_key(project_id: int, file_uid: uuid.UUID) -> str:
        return f"file_info:{project_id}:{file_uid}"

    async def getFileContent(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[bytes, FileNotFoundInSystemError]:
        """Retrieve file content by UUID."""
        res = await self.getFileInfo(file_uid, project_id)
        if res.status == ResultStatus.Err:
            return res.into()
        file_record = res.unwrap()
        file_content = await asyncio.to_thread(
            self._loadFileContentFromStorage,
            file_record["storage_path"],
        )
        return Ok(file_content)

    async def getFileInfoAndContent(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[tuple[FileRecord, bytes], FileNotFoundInSystemError]:
        """Retrieve file info and content by UUID."""
        res = await self.getFileInfo(file_uid, project_id)
        if res.status == ResultStatus.Err:
            return res.into()
        file_record = res.unwrap()
        file_content = await asyncio.to_thread(
            self._loadFileContentFromStorage,
            file_record["storage_path"],
        )
        return Ok((file_record, file_content))

    async def getFileUrl(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[str, FileNotFoundInSystemError]:
        """Generate a presigned URL for the file by UUID."""
        res = await self.getFileInfo(file_uid, project_id)
        if res.status == ResultStatus.Err:
            return res.into()
        file_record = res.unwrap()
        url = self.storage_backend.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.file_storage_settings.s3_bucket_name,
                "Key": file_record["storage_path"],
            },
            ExpiresIn=self.file_storage_settings.s3_presigned_url_expiry_seconds,
        )
        return Ok(url)

    async def getFileInfoAndUrl(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[tuple[str, FileRecord], FileNotFoundInSystemError]:
        """Generate a presigned URL for the file by UUID."""
        res = await self.getFileInfo(file_uid, project_id)
        if res.status == ResultStatus.Err:
            return res.into()
        file_record = res.unwrap()
        url = self.storage_backend.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.file_storage_settings.s3_bucket_name,
                "Key": file_record["storage_path"],
            },
            ExpiresIn=self.file_storage_settings.s3_presigned_url_expiry_seconds,
        )
        return Ok((url, file_record))

    async def getFileInfo(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[FileRecord, FileNotFoundInSystemError]:
        """Retrieve file info by UUID."""
        cache_key = FileStorageService._cache_key(project_id, file_uid)
        cached_info = await self.redis.get(cache_key)
        if cached_info:
            json_data = json.loads(cached_info)
            return Ok(
                FileRecord(
                    {
                        "id": json_data["id"],
                        "uid": uuid.UUID(json_data["uid"]),
                        "filename": json_data["filename"],
                        "storage_path": json_data["storage_path"],
                        "mime_type": json_data["mime_type"],
                        "size": json_data["size"],
                        "created_at": datetime.fromisoformat(
                            json_data["created_at"]
                        ),
                        "extra_metadata": json_data["extra_metadata"],
                    }
                )
            )

        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.getAvailableByUUID(
                session, file_uid, project_id
            )
            if not file_record or file_record.status != FileStatus.AVAILABLE:
                return Err(FileNotFoundInSystemError())

            res: FileRecord = {
                "id": file_record.id,
                "uid": file_record.uuid,
                "filename": file_record.original_filename,
                "storage_path": file_record.filepath,
                "mime_type": file_record.mime_type,
                "size": file_record.size_in_bytes,
                "created_at": file_record.created_at,
                "extra_metadata": file_record.extra_metadata,
            }

        await self.redis.set(
            cache_key,
            json.dumps(res, default=json_serializer),
            ex=self.file_storage_settings.redis_cache_expiry_seconds,
        )
        return Ok(res)

    async def updateFileMetadata(
        self, file_uid: uuid.UUID, project_id: int, extra_metadata: dict | None
    ) -> Result[None, FileNotFoundInSystemError]:
        """Update file metadata by UUID."""
        cache_key = FileStorageService._cache_key(project_id, file_uid)
        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.updateExtraMetadataByUUID(
                session, file_uid, project_id, extra_metadata
            )
            if not file_record:
                return Err(FileNotFoundInSystemError())

            await session.commit()
        await self.redis.delete(cache_key)  # Invalidate cache
        return Ok(None)

    def _deleteFileFromStorage(self, file_path: str) -> None:
        self.storage_backend.delete_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_path,
        )

    async def deleteFile(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[None, FileNotFoundInSystemError]:
        """Delete a file from storage and remove its metadata."""
        cache_key = FileStorageService._cache_key(project_id, file_uid)

        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.markFileAsDeletedByUUID(
                session, file_uid, project_id
            )
            if not file_record:
                return Err(FileNotFoundInSystemError())
            file_path = file_record.filepath
            file_id = file_record.id
            await session.commit()

        await self.redis.delete(cache_key)  # Invalidate cache
        await asyncio.to_thread(self._deleteFileFromStorage, file_path)

        async with self.session_manager.get_session() as session:
            await self.file_repo.deleteFileById(session, file_id)
            await session.commit()
        return Ok(None)

    async def listFilesInProject(self, project_id: int) -> list[FileRecord]:
        """List all available files for a project."""
        async with self.session_manager.get_session() as session:
            file_records = await self.file_repo.getFileListByProjectID(
                session, project_id
            )
            return [
                {
                    "id": file_record.id,
                    "uid": file_record.uuid,
                    "filename": file_record.original_filename,
                    "storage_path": file_record.filepath,
                    "mime_type": file_record.mime_type,
                    "size": file_record.size_in_bytes,
                    "created_at": file_record.created_at,
                    "extra_metadata": file_record.extra_metadata,
                }
                for file_record in file_records
            ]

    async def cleanupJob(self):
        """Background job to clean up deleted files from storage."""
        async with self.session_manager.get_session() as session:
            stmt = select(File).where(
                or_(
                    and_(
                        File.status == FileStatus.DELETED,
                        File.updated_at
                        < datetime.now(UTC).replace(tzinfo=None)
                        - timedelta(hours=1),
                    ),
                    and_(
                        File.status == FileStatus.UPLOADING,
                        File.created_at
                        < datetime.now(UTC).replace(tzinfo=None)
                        - timedelta(hours=1),
                    ),
                )
            )

            deleted_files = (await session.execute(stmt)).scalars().all()
            deleted_file_info = [
                {
                    "id": file_record.id,
                    "filepath": file_record.filepath,
                }
                for file_record in deleted_files
            ]

        for file_record in deleted_file_info:
            try:
                await asyncio.to_thread(
                    self._deleteFileFromStorage, file_record["filepath"]
                )
                async with self.session_manager.get_session() as session:
                    await self.file_repo.deleteFileById(
                        session, file_record["id"]
                    )
                    await session.commit()
            except Exception as e:
                pass  # let the next cleanup job try again, we don't want to block on this
