from gantry.db import Repository

from ..models import (
    BillingSource,
    BillingSourceProvider,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BillingSourceRepo(Repository[BillingSource, int]):
    def __init__(self):
        super().__init__(BillingSource, BillingSource.id)

    async def getForOrg(
        self, session: AsyncSession, org_id: str
    ) -> BillingSource | None:
        stmt = select(BillingSource).where(
            BillingSource.organization_id == org_id
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def getWithLock(
        self,
        session: AsyncSession,
        org_id: str,
        provider: BillingSourceProvider,
        read: bool = False,
    ) -> BillingSource | None:
        stmt = select(BillingSource).where(
            BillingSource.organization_id == org_id,
            BillingSource.source_type == provider,
        )
        if read:
            stmt = stmt.with_for_update(read=True)
        else:
            stmt = stmt.with_for_update()
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
