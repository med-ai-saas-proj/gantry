from src.db.repository import Repository
from src.management.billing.models import (
    BillingSource,
    BillingSourceProvider,
)

from typing import Sequence

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
