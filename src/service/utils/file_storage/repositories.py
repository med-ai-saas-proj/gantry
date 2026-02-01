from src.db.repository import Repository
from src.service.utils.file_storage.models import File

from sqlalchemy import select


class FileRepository(Repository):
    """File repository."""

    def __init__(self):
        """Initialize FileRepository."""
        super().__init__(File, File.id)

    async def getByUUID(self, session, file_uuid: str) -> File | None:
        """Get file by UUID."""
        stmt = select().where(File.uuid == file_uuid).limit(1)
        return await self.selectOne(session, stmt)
