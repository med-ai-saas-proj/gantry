from typing import Sequence
from src.db.repository import Repository
from src.service.utils.file_storage.models import File, FileStatus

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio.session import AsyncSession


class FileRepository(Repository):
    """File repository."""

    def __init__(self):
        """Initialize FileRepository."""
        super().__init__(File, File.id)

    async def getAvailableByUUID(
        self, session: AsyncSession, file_uuid: uuid.UUID, project_id: int
    ) -> File | None:
        """Get file by UUID."""
        stmt = (
            select(File)
            .select_from(File)
            .where(
                (File.uuid == file_uuid)
                & (File.status == FileStatus.AVAILABLE)
                & (File.project_id == project_id)
            )
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def getFileListByProjectID(
        self, session: AsyncSession, project_id: int
    ) -> Sequence[File]:
        """Get file list by project ID."""
        stmt = (
            select(File)
            .select_from(File)
            .where(
                (File.project_id == project_id)
                & (File.status == FileStatus.AVAILABLE)
            )
        )
        return await self.selectMany(session, stmt)

    async def deleteFileByUUID(
        self, session: AsyncSession, file_id: int
    ) -> None:
        """Delete Marked Deleted file by ID."""
        stmt = delete(File).where(
            (File.id == file_id) & (File.status == FileStatus.DELETED)
        )
        await session.execute(stmt)

    async def markFileAsAvailableById(
        self, session: AsyncSession, file_id: int
    ) -> File | None:
        """Mark file as available by ID after upload."""
        stmt = (
            update(File)
            .where((File.id == file_id) & (File.status == FileStatus.UPLOADING))
            .values(status=FileStatus.AVAILABLE)
            .returning(File)
        )
        res = await session.execute(stmt)
        file_record = res.scalar_one_or_none()
        return file_record if file_record else None

    async def markFileAsDeletedByUUID(
        self, session: AsyncSession, file_uuid: uuid.UUID, project_id: int
    ) -> File | None:
        """Mark file as deleted by UUID."""
        stmt = (
            update(File)
            .where(
                (File.uuid == file_uuid)
                & (File.project_id == project_id)
                & (File.status == FileStatus.AVAILABLE)
            )
            .values(status=FileStatus.DELETED)
        ).returning(File)
        res = await session.execute(stmt)
        file_record = res.scalar_one_or_none()
        return file_record if file_record else None

    async def updateExtraMetadataByUUID(
        self,
        session: AsyncSession,
        file_uuid: uuid.UUID,
        project_id: int,
        extra_metadata: dict | None,
    ) -> File | None:
        """Update file extra metadata by UUID."""
        stmt = (
            update(File)
            .where(
                (File.uuid == file_uuid)
                & (File.project_id == project_id)
                & (File.status == FileStatus.AVAILABLE)
            )
            .values(extra_metadata=extra_metadata)
            .returning(File)
        )
        res = await session.execute(stmt)
        file_record = res.scalar_one_or_none()
        return file_record if file_record else None