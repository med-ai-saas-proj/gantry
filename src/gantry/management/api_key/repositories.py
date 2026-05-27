"""API key repository."""

from gantry.db import Repository, CacheRepository
from gantry.management.project import Project, ProjectSettings
from gantry.management.organization import OrgSettings

from .models import ApiKey
from .entities import ApiKeyInfo, ApiKeyContextRecord

from uuid import UUID
from typing import Sequence

from sqlalchemy import func, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class ApiKeyRepository(Repository[ApiKey, int]):
    """Repository for project-scoped API keys."""

    def __init__(self, cache_repo: CacheRepository):
        self.cache_repo = cache_repo
        super().__init__(ApiKey, ApiKey.id)

    @staticmethod
    def contextRecordCacheKey(hashed_key: str) -> str:
        return f"api_keys:context_record:{hashed_key}"

    async def invalidateContextRecordCache(self, hashed_key: str) -> None:
        """Drop cached runtime context after mutable API-key changes."""
        if not hashed_key:
            return
        await self.cache_repo.invalidateCached(
            self.contextRecordCacheKey(hashed_key)
        )

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

    async def getContextByHashedKey(
        self,
        session: AsyncSession,
        hashed_key: str,
    ) -> ApiKeyContextRecord | None:
        stmt = (
            select(
                ApiKey.id.label("api_key_id"),
                ApiKey.uuid.label("api_key_uuid"),
                ApiKey.user_id,
                ApiKey.project_id,
                ApiKey.hashed_key,
                ApiKey.permissions,
                ApiKey.disabled,
                Project.uuid.label("project_uuid"),
                Project.organization_id.label("organization_uuid"),
                OrgSettings.rate_limit.label("organization_rate_limit"),
                OrgSettings.spending_limit.label("organization_spending_limit"),
                ProjectSettings.rate_limit.label("project_rate_limit"),
                ProjectSettings.spending_limit.label("project_spending_limit"),
            )
            .select_from(ApiKey)
            .join(Project, ApiKey.project_id == Project.id)
            .outerjoin(
                OrgSettings,
                OrgSettings.org_id == Project.organization_id,
            )
            .outerjoin(
                ProjectSettings,
                ProjectSettings.project_id == Project.id,
            )
            .where(ApiKey.hashed_key == hashed_key)
            .limit(1)
        )

        async def _inner():
            row = (await session.execute(stmt)).mappings().first()
            if row is None:
                return None
            return ApiKeyContextRecord(
                api_key_id=int(row["api_key_id"]),
                api_key_uuid=row["api_key_uuid"],
                user_uuid=str(row["user_id"]),
                project_id=int(row["project_id"]),
                # org_id=str(row["organization_uuid"]),
                organization_uuid=str(row["organization_uuid"]),
                project_uuid=str(row["project_uuid"]),
                hashed_key=str(row["hashed_key"]),
                permissions=list(row["permissions"] or []),
                disabled=bool(row["disabled"]),
                rpm_limit_organization=(
                    int(row["organization_rate_limit"])
                    if row["organization_rate_limit"] is not None
                    else None
                ),
                rpm_limit_project=(
                    int(row["project_rate_limit"])
                    if row["project_rate_limit"] is not None
                    else None
                ),
                spending_limit_organization=(
                    int(row["organization_spending_limit"])
                    if row["organization_spending_limit"] is not None
                    else None
                ),
                spending_limit_project=(
                    int(row["project_spending_limit"])
                    if row["project_spending_limit"] is not None
                    else None
                ),
            )

        return await self.cache_repo.getCachedOrCall(
            self.contextRecordCacheKey(hashed_key), _inner
        )

    async def getByHashedKeys(
        self, session: AsyncSession, hashed_keys: list[str]
    ) -> Sequence[ApiKeyInfo]:
        stmt = (
            select(
                ApiKey.uuid,
                ApiKey.hashed_key,
                ApiKey.user_id,
                ApiKey.project_id,
                ApiKey.id,
                ApiKey.permissions,
                Project.uuid.label("project_uuid"),
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
                    "api_key_id": int(key["id"]),
                    "api_key_uuid": str(key["uuid"]),
                    "user_uuid": str(key["user_id"]),
                    "project_id": int(key["project_id"]),
                    "project_uuid": str(key["project_uuid"]),
                    # "org_id": str(key["organization_id"]),
                    "organization_uuid": str(key["organization_id"]),
                    "hashed_key": str(key["hashed_key"]),
                    "permissions": list(key["permissions"] or []),
                    "rpm_limit_organization": -1,
                    "rpm_limit_project": -1,
                    "spending_limit_organization": -1,
                    "spending_limit_project": -1,
                }
            )
            for key in result.mappings().all()
        ]

    async def getByProjectId(
        self,
        session: AsyncSession,
        project_id: int,
        disabled: bool | None = None,
    ) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .select_from(ApiKey)
            .where(ApiKey.project_id == project_id)
            .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        )
        if disabled is not None:
            stmt = stmt.where(ApiKey.disabled == disabled)
        return list(await self.selectMany(session, stmt))

    async def countByProjectId(
        self,
        session: AsyncSession,
        project_id: int,
        disabled: bool | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.project_id == project_id)
        )
        if disabled is not None:
            stmt = stmt.where(ApiKey.disabled == disabled)
        res = await session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def countAll(self, session: AsyncSession) -> int:
        stmt = select(func.count()).select_from(ApiKey)
        res = await session.execute(stmt)
        return int(res.scalar_one() or 0)

    async def getByUuid(
        self, session: AsyncSession, api_key_uuid: str
    ) -> ApiKey | None:
        stmt = (
            select(ApiKey)
            .select_from(ApiKey)
            .where(ApiKey.uuid == api_key_uuid)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def create(
        self,
        session: AsyncSession,
        *,
        api_key_uuid: UUID,
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
                uuid=api_key_uuid,
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
        disabled: bool | None = None,
    ) -> ApiKey | None:
        values = {
            "name": name,
            "description": description,
            "permissions": permissions,
        }
        if disabled is not None:
            values["disabled"] = disabled
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == api_key_id)
            .values(**values)
            .returning(ApiKey)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def updateByUuid(
        self,
        session: AsyncSession,
        api_key_uuid: str,
        *,
        name: str,
        description: str,
        permissions: list[str],
        disabled: bool | None = None,
    ) -> ApiKey | None:
        values = {
            "name": name,
            "description": description,
            "permissions": permissions,
        }
        if disabled is not None:
            values["disabled"] = disabled
        stmt = (
            update(ApiKey)
            .where(ApiKey.uuid == api_key_uuid)
            .values(**values)
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

    async def updateDisabledByUuid(
        self,
        session: AsyncSession,
        api_key_uuid: str,
        *,
        disabled: bool,
    ) -> ApiKey | None:
        stmt = (
            update(ApiKey)
            .where(ApiKey.uuid == api_key_uuid)
            .values(disabled=disabled)
            .returning(ApiKey)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def deleteById(self, session: AsyncSession, api_key_id: int) -> bool:
        stmt = (
            delete(ApiKey).where(ApiKey.id == api_key_id).returning(ApiKey.id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def deleteByUuid(
        self, session: AsyncSession, api_key_uuid: str
    ) -> bool:
        stmt = (
            delete(ApiKey)
            .where(ApiKey.uuid == api_key_uuid)
            .returning(ApiKey.id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None
