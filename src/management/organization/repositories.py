"""Repositories for Organization Postgres models."""

from src.db.repository import Repository

from .models import (
    OrgSettings,
    OrgDeletionRequest,
)

from datetime import datetime

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


class OrgSettingsRepository(Repository[OrgSettings, str]):
    """Repository for OrgSettings (keyed by org_id)."""

    def __init__(self):
        super().__init__(OrgSettings, OrgSettings.org_id)

    async def getOrCreate(
        self, session: AsyncSession, org_id: str
    ) -> OrgSettings:
        """Return existing settings or create default ones."""
        existing = await self.getByKey(session, org_id)
        if existing is not None:
            return existing
        new_settings = OrgSettings(org_id=org_id, extra={})
        session.add(new_settings)
        await session.flush()
        return new_settings

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        rate_limit: int | None,
        extra: dict,
    ) -> OrgSettings:
        """Create or update settings for an organization."""
        stmt = (
            insert(OrgSettings)
            .values(
                org_id=org_id,
                rate_limit=rate_limit,
                extra=extra,
            )
            .on_conflict_do_update(
                index_elements=[OrgSettings.org_id],
                set_={
                    "rate_limit": rate_limit,
                    "extra": extra,
                    "updated_at": func.now(),
                },
            )
            .returning(OrgSettings)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deleteByOrgId(self, session: AsyncSession, org_id: str) -> bool:
        record = await self.getByKey(session, org_id)
        if record is None:
            return False
        await session.delete(record)
        await session.flush()
        return True


class OrgDeletionRequestRepository(Repository[OrgDeletionRequest, int]):
    """Repository for organization deletion requests."""

    def __init__(self):
        super().__init__(OrgDeletionRequest, OrgDeletionRequest.id)

    async def getByOrgId(
        self, session: AsyncSession, org_id: str
    ) -> OrgDeletionRequest | None:
        stmt = (
            select(OrgDeletionRequest)
            .where(OrgDeletionRequest.org_id == org_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def create(
        self,
        session: AsyncSession,
        entity: OrgDeletionRequest,
    ) -> OrgDeletionRequest:
        session.add(entity)
        await session.flush()
        return entity

    async def upsertRequest(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> OrgDeletionRequest:
        stmt = (
            insert(OrgDeletionRequest)
            .values(org_id=org_id)
            .on_conflict_do_update(
                index_elements=[OrgDeletionRequest.org_id],
                set_={"requested_at": OrgDeletionRequest.requested_at},
            )
            .returning(OrgDeletionRequest)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deleteByOrgId(self, session: AsyncSession, org_id: str) -> bool:
        record = await self.getByOrgId(session, org_id)
        if record is None:
            return False
        await session.delete(record)
        await session.flush()
        return True

    async def listDueRequests(
        self,
        session: AsyncSession,
        due_before_or_equal: datetime,
        limit: int = 100,
    ) -> list[OrgDeletionRequest]:
        stmt = (
            select(OrgDeletionRequest)
            .where(OrgDeletionRequest.requested_at <= due_before_or_equal)
            .order_by(OrgDeletionRequest.requested_at.asc())
            .limit(limit)
        )
        return await self.selectAll(session, stmt)
