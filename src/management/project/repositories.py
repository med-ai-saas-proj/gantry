"""Repositories for Project module models."""

from src.db.repository import Repository
from src.shared.utils.uuid_utils import uuid7

from .models import Project, ProjectMembership

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


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
        await session.refresh(project)
        return project

    async def get_by_uuid(
        self, session: AsyncSession, project_uuid: str
    ) -> Project | None:
        try:
            parsed = UUID(project_uuid)
        except ValueError:
            return None
        stmt = select(Project).where(Project.uuid == parsed).limit(1)
        return await self.selectOne(session, stmt)

    async def list_by_org(
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

    async def list_by_member(
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

    async def get_membership(
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

    async def upsert_membership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> ProjectMembership:
        existing = await self.get_membership(session, project_id, user_id)
        if existing is None:
            existing = ProjectMembership(
                project_id=project_id,
                user_id=user_id,
            )
            session.add(existing)
        await session.flush()
        await session.refresh(existing)
        return existing

    async def delete_membership(
        self,
        session: AsyncSession,
        project_id: int,
        user_id: str,
    ) -> bool:
        existing = await self.get_membership(session, project_id, user_id)
        if existing is None:
            return False
        await session.delete(existing)
        await session.flush()
        return True

    async def list_members(
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

    async def list_memberships_for_user_in_org(
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

    async def count_members(
        self, session: AsyncSession, project_id: int
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
        )
        res = await session.execute(stmt)
        return int(res.scalar() or 0)
