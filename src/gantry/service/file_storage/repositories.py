from gantry.db import Repository

from .models import File, FileStatus

import uuid
from typing import Sequence

from sqlalchemy import and_, text, delete, select, update
from sqlalchemy.ext.asyncio.session import AsyncSession


class FileRepository(Repository):
    """File repository."""

    def __init__(self):
        """Initialize FileRepository."""
        super().__init__(File, File.id)

    async def getAvailableIdsByUUIDs(
        self,
        session: AsyncSession,
        file_uids: Sequence[uuid.UUID],
        project_id: int,
    ) -> Sequence[File]:
        """Get file IDs by UUIDs."""
        stmt = select(File).where(
            File.uuid.in_(file_uids)
            & (File.project_id == project_id)
            & (File.status == FileStatus.AVAILABLE)
        )
        res = await session.execute(stmt)
        files = res.scalars().all()
        return files

    async def getAvailableIdsByMetadata(
        self,
        session: AsyncSession,
        metadata_filters: dict[str, str | int | float],
        project_id: int,
    ) -> Sequence[File]:
        """Get file IDs by metadata filters."""
        stmt = select(File).where(
            File.project_id == project_id, File.status == FileStatus.AVAILABLE
        )

        if metadata_filters:
            filters = []
            for key, value in metadata_filters.items():
                filters.append(File.extra_metadata[key].astext == str(value))

            stmt = stmt.where(and_(*filters))

        res = await session.execute(stmt.params(**metadata_filters))
        files = res.scalars().all()
        return files

    async def getAvailableByIds(
        self, session: AsyncSession, file_ids: Sequence[int]
    ) -> Sequence[File]:
        """Get files by IDs."""
        stmt = (
            select(File)
            .select_from(File)
            .where(
                (File.id.in_(file_ids)) & (File.status == FileStatus.AVAILABLE)
            )
        )
        res = await session.execute(stmt)
        return res.scalars().all()

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

    async def deleteFileById(self, session: AsyncSession, file_id: int) -> File:
        """Delete Marked Deleted file by ID."""
        stmt = (
            delete(File)
            .where((File.id == file_id) & (File.status == FileStatus.DELETED))
            .returning(File)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def markFileAsAvailableById(
        self, session: AsyncSession, file_id: int
    ) -> File:
        """Mark file as available by ID after upload."""
        stmt = (
            update(File)
            .where((File.id == file_id) & (File.status == FileStatus.UPLOADING))
            .values(status=FileStatus.AVAILABLE)
            .returning(File)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

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
        return res.scalar_one_or_none()

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
        return res.scalar_one_or_none()
