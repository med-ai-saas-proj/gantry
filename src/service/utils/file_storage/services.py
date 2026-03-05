from src.db.session import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .types import FileRecord
from .models import File, FileStatus
from .settings import ObjectStorageSettings
from .repositories import FileRepository

import uuid
import asyncio
from typing import TYPE_CHECKING, BinaryIO, cast

from safe_result import Ok, Err, Result


class FileNotFoundInSystemError(RecoverableError):
    status = 404
    code = "file_not_found"
    title = "File not found"
    detail = "The requested file was not found in storage."


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
        ):
            self.storage_backend = storage_backend
            self.session_manager = session_manager
            self.file_storage_settings = file_storage_settings
            self.file_repo = file_repo
    else:

        def __init__(
            self,
            storage_backend,
            session_manager: AsyncSessionManager,
            file_storage_settings: ObjectStorageSettings,
            file_repo: FileRepository,
        ):
            self.storage_backend = storage_backend
            self.session_manager = session_manager
            self.file_storage_settings = file_storage_settings
            self.file_repo = file_repo

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
    ):
        """Upload a file and store its metadata."""
        if file_uid is None:
            file_uid = uuid.uuid4()
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

    async def getFileContent(
        self, file_uuid: uuid.UUID, project_id: int
    ) -> Result[bytes, FileNotFoundInSystemError]:
        """Retrieve file content by UUID."""
        res = await self.getFileMetadata(file_uuid, project_id)
        if isinstance(res, Err):
            return res
        file_record = res.unwrap()
        file_content = await asyncio.to_thread(
            self._loadFileContentFromStorage,
            file_record["storage_path"],
        )
        return Ok(file_content)

    async def getFileUrl(
        self, file_uuid: uuid.UUID, project_id: int
    ) -> Result[str, FileNotFoundInSystemError]:
        """Generate a presigned URL for the file by UUID."""
        res = await self.getFileMetadata(file_uuid, project_id)
        if isinstance(res, Err):
            return res
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

    async def getFileMetadataAndUrl(
        self, file_uuid: uuid.UUID, project_id: int
    ) -> Result[tuple[str, FileRecord], FileNotFoundInSystemError]:
        """Generate a presigned URL for the file by UUID."""
        res = await self.getFileMetadata(file_uuid, project_id)
        if isinstance(res, Err):
            return res
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

    async def getFileMetadata(
        self, file_uuid: uuid.UUID, project_id: int
    ) -> Result[FileRecord, FileNotFoundInSystemError]:
        """Retrieve file metadata by UUID."""
        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.getAvailableByUUID(
                session, file_uuid, project_id
            )
            if not file_record or file_record.status != FileStatus.AVAILABLE:
                return Err(FileNotFoundInSystemError())

            return Ok[FileRecord](
                {
                    "id": str(file_record.uuid),
                    "filename": file_record.original_filename,
                    "storage_path": file_record.filepath,
                    "mime_type": file_record.mime_type,
                    "size": file_record.size_in_bytes,
                    "created_at": file_record.created_at,
                }
            )

    def _deleteFileFromStorage(self, file_path: str) -> None:
        self.storage_backend.delete_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_path,
        )

    async def deleteFile(
        self, file_uid: uuid.UUID, project_id: int
    ) -> Result[None, FileNotFoundInSystemError]:
        """Delete a file from storage and remove its metadata."""
        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.markFileAsDeletedByUUID(
                session, file_uid, project_id
            )
            if not file_record:
                return Err(FileNotFoundInSystemError())
            file_path = file_record.filepath
            file_id = file_record.id
            await session.commit()

        await asyncio.to_thread(self._deleteFileFromStorage, file_path)

        async with self.session_manager.get_session() as session:
            await self.file_repo.deleteFileByUUID(session, file_id)
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
                    "id": str(file_record.uuid),
                    "filename": file_record.original_filename,
                    "storage_path": file_record.filepath,
                    "mime_type": file_record.mime_type,
                    "size": file_record.size_in_bytes,
                    "created_at": file_record.created_at,
                }
                for file_record in file_records
            ]
