from typing import Sequence
from src.db.repository import Repository
from src.service.utils.file_storage.models import File, FileStatus

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession


class FileRepository(Repository):
    """File repository."""

    def __init__(self):
        """Initialize FileRepository."""
        super().__init__(File, File.id)

    async def getByUUID(self,
        session: AsyncSession,
        file_uuid: uuid.UUID,
        project_id: int
    ) -> File | None:
        """Get file by UUID."""
        stmt = select(File).where(
            (File.uuid == file_uuid)
            & (File.status == FileStatus.AVAILABLE)
            & (File.project_id == project_id)
        ).limit(1)
        return await self.selectOne(session, stmt)

    async def getUploadingByUUID(
        self,
        session: AsyncSession,
        file_uuid: uuid.UUID
    ) -> File | None:
        """Get uploading file by UUID."""
        stmt = select(File).where((File.uuid == file_uuid) & (File.status == FileStatus.UPLOADING)).limit(1)
        return await self.selectOne(session, stmt)

    async def getFileListByProjectID(
        self,
        session: AsyncSession,
        project_id: int
    ) -> Sequence[File]:
        """Get file list by project ID."""
        stmt = select(File).where(
            (File.project_id == project_id) & (File.status == FileStatus.AVAILABLE)
        )
        return await self.selectMany(session, stmt)