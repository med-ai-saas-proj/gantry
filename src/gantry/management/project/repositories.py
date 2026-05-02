"""Repositories for Project module models."""

from gantry.db.repository import Repository
from gantry.shared.utils.uuid_utils import uuid7

from .models import Project, ProjectMember, ProjectSettings

from uuid import UUID

from sqlalchemy import func, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert


class ProjectRepository(Repository[Project, int]):
    """Repository for Project table."""

    def __init__(self):
        super().__init__(Project, Project.id)

    async def create(
        self,
        session: AsyncSession,
        name: str,
        description: str | None,
        organization_id: str,
    ) -> Project:
        stmt = (
            insert(Project)
            .values(
                uuid=uuid7(),
                name=name,
                description=description,
                organization_id=organization_id,
            )
            .returning(Project)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def getByUuid(
        self, session: AsyncSession, project_uuid: str
    ) -> Project | None:
        try:
            parsed = UUID(project_uuid)
        except ValueError:
            return None
        stmt = (
            select(Project)
            .select_from(Project)
            .where(Project.uuid == parsed)
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def updateById(
        self,
        session: AsyncSession,
        project_id: int,
        *,
        name: str,
        description: str | None,
    ) -> Project | None:
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(
                name=name,
                description=description,
            )
            .returning(Project)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def listByOrg(
        self,
        session: AsyncSession,
        organization_id: str,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .select_from(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def listByMember(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str | None = None,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .select_from(Project)
            .join(
                ProjectMember,
                ProjectMember.project_id == Project.id,
            )
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def countAll(self, session: AsyncSession) -> int:
        """Return the total number of projects."""
        stmt = select(func.count()).select_from(Project)
        res = await session.execute(stmt)
        return int(res.scalar_one() or 0)


class ProjectMemberRepository(Repository[ProjectMember, int]):
    """Repository for project memberships."""

    def __init__(self):
        super().__init__(ProjectMember, ProjectMember.project_id)

    async def getMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> ProjectMember | None:
        stmt = (
            select(ProjectMember)
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.user_id == user_id)
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def upsertMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> ProjectMember:
        stmt = (
            pg_insert(ProjectMember)
            .values(
                project_id=project_id,
                user_id=user_id,
            )
            .on_conflict_do_update(
                index_elements=[
                    ProjectMember.project_id,
                    ProjectMember.user_id,
                ],
                set_={"updated_at": func.now()},
            )
            .returning(ProjectMember)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deleteMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> bool:
        stmt = (
            delete(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .returning(ProjectMember.project_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def listMembers(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def listMembershipsForUserInOrg(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str,
    ) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .select_from(ProjectMember)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .where(Project.organization_id == organization_id)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def countMembers(self, session: AsyncSession, project_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        res = await session.execute(stmt)
        return int(res.scalar() or 0)


class ProjectSettingsRepository(Repository[ProjectSettings, int]):
    """Repository for project settings."""

    def __init__(self):
        super().__init__(ProjectSettings, ProjectSettings.project_id)

    async def getOrCreate(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> ProjectSettings:
        """Return existing settings or insert a default row atomically."""
        insert_stmt = pg_insert(ProjectSettings).values(project_id=project_id)
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[ProjectSettings.project_id],
            set_={"project_id": insert_stmt.excluded.project_id},
        ).returning(ProjectSettings)
        res = await session.execute(stmt)
        return res.scalar_one()

    async def upsert(
        self,
        session: AsyncSession,
        project_id: int,
        rate_limit: int | None,
        spending_limit: int | None,
        extra: dict,
    ) -> ProjectSettings:
        stmt = (
            pg_insert(ProjectSettings)
            .values(
                project_id=project_id,
                rate_limit=rate_limit,
                spending_limit=spending_limit,
                extra=extra,
            )
            .on_conflict_do_update(
                index_elements=[ProjectSettings.project_id],
                set_={
                    "rate_limit": rate_limit,
                    "spending_limit": spending_limit,
                    "extra": extra,
                    "updated_at": func.now(),
                },
            )
            .returning(ProjectSettings)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def deleteByProjectId(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> bool:
        stmt = (
            delete(ProjectSettings)
            .where(ProjectSettings.project_id == project_id)
            .returning(ProjectSettings.project_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None
