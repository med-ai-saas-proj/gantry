"""API key repository."""

from gantry.db.repository import Repository
from gantry.management.project.models import Project
from gantry.management.api_keys.entities import ApiKeyInfo

from .models import ApiKey

from typing import Sequence

from sqlalchemy import func, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class ApiKeyRepository(Repository[ApiKey, int]):
    """Repository for project-scoped API keys."""

    def __init__(self):
        super().__init__(ApiKey, ApiKey.id)

    async def getByHashedKey(
        self, session: AsyncSession, hashed_key: str
    ) -> ApiKey | None:
        stmt = (
            select(ApiKey)
            .select_from(ApiKey)
            .where(ApiKey.hashed_key == hashed_key)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def getByHashedKeys(
        self, session: AsyncSession, hashed_keys: list[str]
    ) -> Sequence[ApiKeyInfo]:
        stmt = (
            select(
                ApiKey.hashed_key,
                ApiKey.user_id,
                ApiKey.project_id,
                ApiKey.id,
                Project.uuid.label("project_uid"),
                Project.organization_id,
            )
            .select_from(ApiKey)
            .join(Project, ApiKey.project_id == Project.id)
            .where(ApiKey.hashed_key.in_(hashed_keys))
        )
        result = await session.execute(stmt)
        return [
            ApiKeyInfo(
                {
                    "api_key_id": key.id,
                    "user_id": str(key.user_id),
                    "project_id": key.project_id,
                    "project_uid": str(key.project_uid),
                    "org_id": key.organization_id,
                    "hashed_key": key.hashed_key,
                }
            )
            for key in result.scalars().all()
        ]

    async def getByProjectId(
        self, session: AsyncSession, project_id: int
    ) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .select_from(ApiKey)
            .where(ApiKey.project_id == project_id)
            .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        )
        return list(await self.selectMany(session, stmt))

    async def countByProjectId(
        self, session: AsyncSession, project_id: int
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.project_id == project_id)
        )
        res = await session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        project_id: int,
        hashed_key: str,
        hint: str,
        name: str,
        description: str,
        permissions: list[str],
    ) -> ApiKey:
        stmt = (
            insert(ApiKey)
            .values(
                user_id=user_id,
                project_id=project_id,
                hashed_key=hashed_key,
                hint=hint,
                name=name,
                description=description,
                permissions=permissions,
            )
            .returning(ApiKey)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def updateById(
        self,
        session: AsyncSession,
        api_key_id: int,
        *,
        name: str,
        description: str,
        permissions: list[str],
    ) -> ApiKey | None:
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(
                name=name,
                description=description,
                permissions=permissions,
            )
            .returning(ApiKey)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def updateDisabledById(
        self,
        session: AsyncSession,
        api_key_id: int,
        *,
        disabled: bool,
    ) -> ApiKey | None:
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(disabled=disabled)
            .returning(ApiKey)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def listDistinctPermissions(
        self,
        session: AsyncSession,
    ) -> list[str]:
        stmt = (
            select(func.unnest(ApiKey.permissions).label("permission"))
            .select_from(ApiKey)
            .distinct()
            .order_by("permission")
        )
        res = await session.execute(stmt)
        return [permission for permission in res.scalars().all() if permission]

    async def deleteById(self, session: AsyncSession, api_key_id: int) -> bool:
        stmt = (
            delete(ApiKey).where(ApiKey.id == api_key_id).returning(ApiKey.id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None
