from src.management.billing.models import Credit, CreditTransaction

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CreditRepo:
    async def getCreditForOrgWithLock(
        self, session: AsyncSession, org_id: str, read: bool = True
    ) -> Credit | None:
        stmt = select(Credit).where(Credit.organization_id == org_id)
        if not read:
            stmt = stmt.with_for_update()
        else:
            stmt = stmt.with_for_update(read=True)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def updateCreditForOrg(
        self, session: AsyncSession, org_id: str, new_amount: Decimal
    ):
        stmt = (
            update(Credit)
            .where(Credit.organization_id == org_id)
            .values(amount=new_amount)
        )
        await session.execute(stmt)

    async def createCreditTransaction(
        self,
        session: AsyncSession,
        org_id: str,
        amount: Decimal,
        description: str,
    ):
        new_transaction = CreditTransaction(
            organization_id=org_id, amount=amount, description=description
        )
        session.add(new_transaction)
