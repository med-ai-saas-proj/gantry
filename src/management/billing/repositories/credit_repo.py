from ..type import CreditTransactionInfo
from ..models import Credit, CreditTransaction

from typing import Sequence
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


class CreditRepo:
    async def getCreditByOrgId(
        self, session: AsyncSession, org_id: str
    ) -> Credit | None:
        stmt = select(Credit).where(Credit.organization_id == org_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def getCreditTransactions(
        self,
        session: AsyncSession,
        org_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[CreditTransactionInfo], int]:
        stmt = (
            select(
                CreditTransaction.amount,
                CreditTransaction.description,
                CreditTransaction.created_at,
                func.count().over().label("total_count"),
            )
            .where(CreditTransaction.organization_id == org_id)
            .order_by(CreditTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()
        return (
            [
                {
                    "amount": row.amount,
                    "description": row.description,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
            rows[0].total_count if rows else 0,
        )

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

    async def addCreditForOrg(
        self, session: AsyncSession, org_id: str, amount: Decimal = Decimal(0)
    ):
        stmt = (
            insert(Credit)
            .values(organization_id=org_id, amount=amount)
            .on_conflict_do_update(
                index_elements=[Credit.organization_id],
                set_=dict(amount=Credit.amount + amount),
            )
            .returning(Credit)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def setCreditForOrg(
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
