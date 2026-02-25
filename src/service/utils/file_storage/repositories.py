from src.db.repository import Repository
from src.service.utils.file_storage.models import File, FileStatus

import uuid

from sqlalchemy import select


class FileRepository(Repository):
    """File repository."""

    def __init__(self):
        """Initialize FileRepository."""
        super().__init__(File, File.id)

    async def getByUUID(self, session, file_uuid: uuid.UUID) -> File | None:
        """Get file by UUID."""
        stmt = select(File).where((File.uuid == file_uuid) & (File.status == FileStatus.AVAILABLE)).limit(1)
        return await self.selectOne(session, stmt)

    async def getUploadingByUUID(self, session, file_uuid: uuid.UUID) -> File | None:
        """Get uploading file by UUID."""
        stmt = select(File).where((File.uuid == file_uuid) & (File.status == FileStatus.UPLOADING)).limit(1)
        return await self.selectOne(session, stmt)