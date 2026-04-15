"""Repositories for Organization Postgres models."""

from gantry.db.repository import Repository

from .models import (
    OrgSettings,
    OrgDeletionRequest,
)

from datetime import datetime

from sqlalchemy import func, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert


class OrgSettingsRepository(Repository[OrgSettings, str]):
    """Repository for OrgSettings (keyed by org_id)."""

    def __init__(self):
        super().__init__(OrgSettings, OrgSettings.org_id)

    async def getOrCreate(
        self, session: AsyncSession, org_id: str
    ) -> OrgSettings:
        """Return existing settings or insert a default row atomically."""
        insert_stmt = pg_insert(OrgSettings).values(org_id=org_id, extra={})
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[OrgSettings.org_id],
            set_={"org_id": insert_stmt.excluded.org_id},
        ).returning(OrgSettings)
        res = await session.execute(stmt)
        return res.scalar_one()

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        rate_limit: int | None,
        spending_limit: int | None,
        extra: dict,
    ) -> OrgSettings:
        """Create or update settings for an organization."""
        stmt = (
            pg_insert(OrgSettings)
            .values(
                org_id=org_id,
                rate_limit=rate_limit,
                spending_limit=spending_limit,
                extra=extra,
            )
            .on_conflict_do_update(
                index_elements=[OrgSettings.org_id],
                set_={
                    "rate_limit": rate_limit,
                    "spending_limit": spending_limit,
                    "extra": extra,
                    "updated_at": func.now(),
                },
            )
            .returning(OrgSettings)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def deleteByOrgId(self, session: AsyncSession, org_id: str) -> bool:
        stmt = (
            delete(OrgSettings)
            .where(OrgSettings.org_id == org_id)
            .returning(OrgSettings.org_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None


class OrgDeletionRequestRepository(Repository[OrgDeletionRequest, int]):
    """Repository for organization deletion requests."""

    def __init__(self):
        super().__init__(OrgDeletionRequest, OrgDeletionRequest.id)

    async def getByOrgId(
        self, session: AsyncSession, org_id: str
    ) -> OrgDeletionRequest | None:
        stmt = (
            select(OrgDeletionRequest)
            .select_from(OrgDeletionRequest)
            .where(OrgDeletionRequest.org_id == org_id)
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        entity: OrgDeletionRequest,
    ) -> OrgDeletionRequest:
        stmt = (
            insert(OrgDeletionRequest)
            .values(org_id=entity.org_id)
            .returning(OrgDeletionRequest)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def upsertRequest(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> OrgDeletionRequest:
        stmt = (
            pg_insert(OrgDeletionRequest)
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
        stmt = (
            delete(OrgDeletionRequest)
            .where(OrgDeletionRequest.org_id == org_id)
            .returning(OrgDeletionRequest.id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def listDueRequests(
        self,
        session: AsyncSession,
        due_before_or_equal: datetime,
        limit: int = 100,
    ) -> list[OrgDeletionRequest]:
        stmt = (
            select(OrgDeletionRequest)
            .select_from(OrgDeletionRequest)
            .where(OrgDeletionRequest.requested_at <= due_before_or_equal)
            .order_by(OrgDeletionRequest.requested_at.asc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())
