from src.db.repository import Repository
from src.management.billing.models import (
    BillingSource,
    BillingSourceProvider,
)

import uuid
from typing import Sequence

from sqlalchemy import select, update
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

    async def getForOrg(
        self, session: AsyncSession, org_id: str
    ) -> BillingSource | None:
        stmt = select(BillingSource).where(
            BillingSource.organization_id == org_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
