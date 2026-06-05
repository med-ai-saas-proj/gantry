"""Repositories for Project module models."""

from gantry.db import Repository
from gantry.db.repositories import CacheRepository
from gantry.shared.utils.uuid_utils import uuid7

from .models import Project, ProjectMember, ProjectSettings

from uuid import UUID

from sqlalchemy import func, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert


class ProjectRepository(Repository[Project, int]):
    """Repository for Project table."""

    PROJECT_CACHE_KEY = "project:by_uuid:{project_uuid}"
    ORG_PROJECTS_CACHE_KEY = "projects:by_org:{organization_id}"

    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo
        super().__init__(Project, Project.id)

    @classmethod
    def getCacheKey(cls, project_uuid: UUID | str):
        return cls.getProjectCacheKey(project_uuid)

    @classmethod
    def getProjectCacheKey(cls, project_uuid: UUID | str):
        return cls.PROJECT_CACHE_KEY.format(
            project_uuid=project_uuid
            if isinstance(project_uuid, str)
            else project_uuid.hex
        )

    @classmethod
    def getOrgProjectsCacheKey(cls, organization_id: str):
        return cls.ORG_PROJECTS_CACHE_KEY.format(
            organization_id=organization_id
        )

    async def invalidateProjectCache(
        self,
        project_uuid: UUID | str,
        organization_id: str | None = None,
    ) -> None:
        await self.cache_repo.invalidateCached(
            self.getProjectCacheKey(project_uuid)
        )
        if organization_id is not None:
            await self.cache_repo.invalidateCached(
                self.getOrgProjectsCacheKey(organization_id)
            )

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
        res = res.scalar_one()
        await self.cache_repo.invalidateCached(
            self.getOrgProjectsCacheKey(organization_id)
        )
        return res

    async def getByUuid(
        self,
        session: AsyncSession,
        project_uuid: str,
        *,
        use_cache: bool = True,
    ) -> Project | None:
        try:
            parsed = UUID(project_uuid)
        except ValueError:
            return None

        async def _load_project():
            stmt = (
                select(Project)
                .select_from(Project)
                .where(Project.uuid == parsed)
                .limit(1)
            )
            return (await session.execute(stmt)).scalar_one_or_none()

        if not use_cache:
            return await _load_project()

        return await self.cache_repo.getCachedOrCall(
            self.getProjectCacheKey(parsed), _load_project
        )

    async def updateByUuid(
        self,
        session: AsyncSession,
        project_uuid: str,
        *,
        name: str,
        description: str | None,
    ) -> Project | None:
        stmt = (
            update(Project)
            .where(Project.uuid == project_uuid, Project.is_archived == False)
            .values(
                name=name,
                description=description,
            )
            .returning(Project)
        )
        res = await session.execute(stmt)
        res = res.scalar_one_or_none()
        if res is not None:
            await self.invalidateProjectCache(
                project_uuid,
                res.organization_id,
            )
        return res

    async def listByOrg(
        self,
        session: AsyncSession,
        organization_id: str,
    ) -> list[Project]:
        async def _load_projects():
            stmt = (
                select(Project)
                .select_from(Project)
                .where(Project.organization_id == organization_id)
                .order_by(Project.created_at.desc())
            )
            return list((await session.execute(stmt)).scalars().all())

        return await self.cache_repo.getCachedOrCall(
            self.getOrgProjectsCacheKey(organization_id), _load_projects
        )

    async def listByMember(
        self,
        session: AsyncSession,
        user_id: str,
        organization_id: str | None,
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
        if organization_id is not None:
            stmt = stmt.where(Project.organization_id == organization_id)

        return list((await session.execute(stmt)).scalars().all())

    async def countAll(self, session: AsyncSession) -> int:
        stmt = select(func.count()).select_from(Project)
        res = await session.execute(stmt)
        return int(res.scalar_one() or 0)


class ProjectMemberRepository(Repository[ProjectMember, int]):
    """Repository for project memberships."""

    CACHE_KEY = "project:memberships:{project_uuid}"

    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo
        super().__init__(ProjectMember, ProjectMember.project_id)

    @classmethod
    def getCacheKey(cls, project_uuid: UUID | str):
        return cls.CACHE_KEY.format(
            project_id=project_uuid
            if isinstance(project_uuid, str)
            else project_uuid.hex
        )

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
        # return (
        #     await self.cache_repo.getCacheOrCall(
        #         self.getCacheKey(project_uuid),
        #         session.execute,
        #         stmt,
        #     )
        # ).scalar_one_or_none()

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

    CACHE_KEY = "project:settings:{project_uuid}"

    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo
        super().__init__(ProjectSettings, ProjectSettings.project_id)

    @classmethod
    def getCacheKey(cls, project_uuid: UUID | str) -> str:
        return cls.CACHE_KEY.format(
            project_uuid=project_uuid
            if isinstance(project_uuid, str)
            else project_uuid.hex
        )

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

    async def getOrCreateByUuid(
        self,
        session: AsyncSession,
        project_uuid: str,
    ) -> ProjectSettings:
        """Return existing settings or insert a default row atomically."""
        _project_uuid = UUID(project_uuid)
        cache_key = self.getCacheKey(project_uuid)

        async def _lamda():
            stmt = (
                select(ProjectSettings)
                .join(Project, Project.id == ProjectSettings.project_id)
                .where(Project.uuid == _project_uuid)
            )
            return (await session.execute(stmt)).scalar_one_or_none()

        res = await self.cache_repo.getCachedOrCall(cache_key, _lamda)
        if res is None:
            stmt = (
                insert(ProjectSettings)
                .from_select(
                    [ProjectSettings.project_id],
                    select(Project).where(Project.uuid == _project_uuid),
                )
                .returning(ProjectSettings)
            )
            res = (await session.execute(stmt)).scalar_one()
            await self.cache_repo.setCache(self.getCacheKey(project_uuid), res)
        return res

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
