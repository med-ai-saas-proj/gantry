from src.db.repository import Repository
from src.management.billing.models import (
    BillingSource,
    BillingSourceState,
    BillingSourceProvider,
)

import uuid
from typing import Sequence
from unittest import result

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class BillingSourceRepo(Repository[BillingSource, int]):
    def __init__(self):
        super().__init__(BillingSource, BillingSource.id)

    async def getByOrgId(
        self,
        session: AsyncSession,
        org_id: str,
        providers: list[BillingSourceProvider] | None = None,
    ) -> Sequence[BillingSource]:
        stmt = select(BillingSource).where(
            BillingSource.organization_id == org_id
        )
        if providers:
            stmt = stmt.where(BillingSource.source_type.in_(providers))
        res = await session.execute(stmt)
        return res.scalars().all()

    async def getByUUID(
        self, session: AsyncSession, billing_source_uuid: uuid.UUID, org_id: str
    ) -> BillingSource | None:
        stmt = select(BillingSource).where(
            (BillingSource.uuid == billing_source_uuid)
            & (BillingSource.organization_id == org_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def markBillingSourceDeletedBuUUID(
        self, session: AsyncSession, billing_source_uuid: uuid.UUID, org_id: str
    ) -> BillingSource | None:
        stmt = (
            update(BillingSource)
            .where(
                (BillingSource.uuid == billing_source_uuid)
                & (BillingSource.organization_id == org_id)
            )
            .values(status=BillingSourceState.DELETED)
            .returning(BillingSource)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def deleteBillingSourceById(
        self, session: AsyncSession, billing_source_id: int
    ) -> BillingSource:
        stmt = (
            delete(BillingSource)
            .where(BillingSource.id == billing_source_id)
            .returning(BillingSource)
        )
        res = await session.execute(stmt)
        return res.scalar_one()

    async def fillProviderInfo(
        self, session: AsyncSession, billing_source_id: int, provider_id: str
    ) -> BillingSource:
        stmt = (
            update(BillingSource)
            .where(BillingSource.id == billing_source_id)
            .values(provider_id=provider_id, status=BillingSourceState.ACTIVE)
            .returning(BillingSource)
        )
        res = await session.execute(stmt)
        return res.scalar_one()
