"""Repositories for Project module models."""

from src.db.repository import Repository
from src.shared.utils.uuid_utils import uuid7

from .models import Project, ProjectMembership

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


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
        project = Project(
            name=name,
            description=description,
            organization_id=organization_id,
        )
        project.uuid = uuid7()
        session.add(project)
        await session.flush()
        return project

    async def getByUuid(
        self, session: AsyncSession, project_uuid: str
    ) -> Project | None:
        try:
            parsed = UUID(project_uuid)
        except ValueError:
            return None
        stmt = select(Project).where(Project.uuid == parsed).limit(1)
        return await self.selectOne(session, stmt)

    async def listByOrg(
        self,
        session: AsyncSession,
        organization_id: str,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc())
        )
        return list(await self.selectMany(session, stmt))

    async def listByMember(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str | None = None,
    ) -> list[Project]:
        stmt = (
            select(Project)
            .join(
                ProjectMembership,
                ProjectMembership.project_id == Project.id,
            )
            .where(ProjectMembership.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        if organization_id:
            stmt = stmt.where(Project.organization_id == organization_id)
        return list(await self.selectMany(session, stmt))


class ProjectMembershipRepository(Repository[ProjectMembership, int]):
    """Repository for project memberships."""

    def __init__(self):
        super().__init__(ProjectMembership, ProjectMembership.project_id)

    async def getMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> ProjectMembership | None:
        stmt = (
            select(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
            .where(ProjectMembership.user_id == user_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def upsertMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> ProjectMembership:
        stmt = (
            insert(ProjectMembership)
            .values(
                project_id=project_id,
                user_id=user_id,
            )
            .on_conflict_do_update(
                index_elements=[
                    ProjectMembership.project_id,
                    ProjectMembership.user_id,
                ],
                set_={"updated_at": func.now()},
            )
            .returning(ProjectMembership)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deleteMembership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> bool:
        existing = await self.getMembership(session, project_id, user_id)
        if existing is None:
            return False
        await session.delete(existing)
        await session.flush()
        return True

    async def listMembers(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> list[ProjectMembership]:
        stmt = (
            select(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
            .order_by(ProjectMembership.joined_at.asc())
        )
        return list(await self.selectMany(session, stmt))

    async def listMembershipsForUserInOrg(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str,
    ) -> list[ProjectMembership]:
        stmt = (
            select(ProjectMembership)
            .join(Project, Project.id == ProjectMembership.project_id)
            .where(ProjectMembership.user_id == user_id)
            .where(Project.organization_id == organization_id)
        )
        return list(await self.selectMany(session, stmt))

    async def countMembers(self, session: AsyncSession, project_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
        )
        res = await session.execute(stmt)
        return int(res.scalar() or 0)
