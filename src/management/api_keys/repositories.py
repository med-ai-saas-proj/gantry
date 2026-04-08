"""API key repository."""

from src.db.repository import Repository
from src.management.project.models import Project, ProjectSettings
from src.management.api_keys.entities import ApiKeyInfo, ApiKeyContextRecord
from src.management.organization.models import OrgSettings

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

    async def getContextByHashedKey(
        self,
        session: AsyncSession,
        hashed_key: str,
    ) -> ApiKeyContextRecord | None:
        stmt = (
            select(
                ApiKey.id.label("api_key_id"),
                ApiKey.user_id,
                ApiKey.project_id,
                ApiKey.hashed_key,
                ApiKey.permissions,
                ApiKey.disabled,
                Project.uuid.label("project_uuid"),
                Project.organization_id.label("organization_uuid"),
                OrgSettings.rate_limit.label("organization_rate_limit"),
                ProjectSettings.rate_limit.label("project_rate_limit"),
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
        row = (await session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return ApiKeyContextRecord(
            api_key_id=int(row["api_key_id"]),
            user_id=str(row["user_id"]),
            project_id=int(row["project_id"]),
            organization_uuid=str(row["organization_uuid"]),
            project_uuid=str(row["project_uuid"]),
            hashed_key=str(row["hashed_key"]),
            permissions=list(row["permissions"] or []),
            disabled=bool(row["disabled"]),
            rpm_limit_organization=(
                int(row["organization_rate_limit"])
                if row["organization_rate_limit"] is not None
                else -1
            ),
            rpm_limit_project=(
                int(row["project_rate_limit"])
                if row["project_rate_limit"] is not None
                else -1
            ),
            spending_limit_organization=-1,
            spending_limit_project=-1,
        )

    async def getByHashedKeys(
        self, session: AsyncSession, hashed_keys: list[str]
    ) -> Sequence[ApiKeyInfo]:
        stmt = (
            select(
                ApiKey.hashed_key,
                ApiKey.user_id,
                ApiKey.project_id,
                ApiKey.id,
                ApiKey.permissions,
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
                    "api_key_id": int(key["id"]),
                    "api_key_uuid": "",
                    "user_id": str(key["user_id"]),
                    "project_id": int(key["project_id"]),
                    "project_uuid": str(key["project_uid"]),
                    "project_uid": str(key["project_uid"]),
                    "org_id": str(key["organization_id"]),
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
