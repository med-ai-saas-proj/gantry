from src.db.session import AsyncSessionManager

from .types import FileRecord
from .models import File, FileType
from .settings import ObjectStorageSettings
from .repositories import FileRepository

import uuid
import asyncio
from typing import TYPE_CHECKING, BinaryIO


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

    def _upload_file(
        self,
        file_name: str,
        file_size: int,
        file_object: BinaryIO | bytes,
        mime_type: str = "application/octet-stream",
    ) -> None:
        self.storage_backend.put_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_name,
            Body=file_object,
            ContentLength=file_size,
            ContentType=mime_type,
        )

    async def upload_file(
        self,
        file_name: str,
        file_data: BinaryIO | bytes,
        file_size: int,
        mime_type: str,
        ext: str,
        file_type: FileType = FileType.GENERAL,
    ):
        """Upload a file and store its metadata."""
        file_key = str(uuid.uuid4())
        file_path = (
            f"uploads/{file_key}.{ext}" if ext else f"/uploads/{file_key}"
        )
        async with self.session_manager.get_session() as session:
            file_record = File(
                original_filename=file_name,
                filepath=file_path,
                mime_type=mime_type,
                size_in_bytes=file_size,
                file_type=file_type,
            )
            session.add(file_record)
            await session.flush()
            file_record_uid = file_record.uuid
            await asyncio.to_thread(
                self._upload_file,
                file_path,
                file_size,
                file_data,
                mime_type,
            )
            await session.commit()
            return file_record_uid

    def _load_file_content(
        self,
        file_path: str,
    ):
        res = self.storage_backend.get_object(
            Bucket=self.file_storage_settings.s3_bucket_name,
            Key=file_path,
        )
        return res["Body"].read()

    async def get_file(self, file_uuid: uuid.UUID) -> bytes:
        """Retrieve file content by UUID."""
        file_record = await self.get_file_metadata(file_uuid)
        file_content = await asyncio.to_thread(
            self._load_file_content,
            file_record["storage_path"],
        )
        return file_content

    async def get_file_url(self, file_uuid: uuid.UUID) -> str:
        """Generate a presigned URL for the file by UUID."""
        file_record = await self.get_file_metadata(file_uuid)
        url = self.storage_backend.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.file_storage_settings.s3_bucket_name,
                "Key": file_record["storage_path"],
            },
            ExpiresIn=self.file_storage_settings.s3_presigned_url_expiry_seconds,
        )
        return url

    async def get_file_metadata_and_url(
        self, file_uuid: uuid.UUID
    ) -> tuple[str, FileRecord]:
        """Generate a presigned URL for the file by UUID."""
        file_record = await self.get_file_metadata(file_uuid)
        url = self.storage_backend.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.file_storage_settings.s3_bucket_name,
                "Key": file_record["storage_path"],
            },
            ExpiresIn=self.file_storage_settings.s3_presigned_url_expiry_seconds,
        )
        return url, file_record

    async def get_file_metadata(self, file_uuid: uuid.UUID) -> FileRecord:
        """Retrieve file metadata by UUID."""
        async with self.session_manager.get_session() as session:
            file_record = await self.file_repo.getByUUID(session, file_uuid)
            if not file_record:
                raise FileNotFoundError(
                    f"File with UUID {file_uuid} not found."
                )

            return {
                "id": str(file_record.uuid),
                "filename": file_record.original_filename,
                "storage_path": file_record.filepath,
                "mime_type": file_record.mime_type,
                "file_type": file_record.file_type,
                "size": file_record.size_in_bytes,
                "created_at": file_record.created_at,
            }
