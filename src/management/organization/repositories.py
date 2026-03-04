"""Repositories for Organization Postgres models."""

from src.db.repository import Repository

from .models import (
    OrgSettings,
    OrgDeletionRequest,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


class OrgSettingsRepository(Repository[OrgSettings, str]):
    """Repository for OrgSettings (keyed by org_id)."""

    def __init__(self):
        super().__init__(OrgSettings, OrgSettings.org_id)

    async def get_or_create(
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
        settings = await self.get_or_create(session, org_id)
        settings.rate_limit = rate_limit
        settings.extra = extra
        await session.flush()
        await session.refresh(settings)
        return settings

    async def delete_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> bool:
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

    async def get_by_org_id(
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

    async def upsert_request(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> OrgDeletionRequest:
        existing = await self.get_by_org_id(session, org_id)
        if existing is None:
            existing = OrgDeletionRequest(
                org_id=org_id,
            )
            session.add(existing)
        await session.flush()
        await session.refresh(existing)
        return existing

    async def delete_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> bool:
        record = await self.get_by_org_id(session, org_id)
        if record is None:
            return False
        await session.delete(record)
        await session.flush()
        return True

    async def list_due_requests(
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
