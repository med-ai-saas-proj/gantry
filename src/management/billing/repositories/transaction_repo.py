from src.db.factories import getTimescaleSessionManager
from src.db.repository import Repository
from src.management.billing.type import AggregatePeriod, BillingAggregateReport
from src.management.billing.models import (
    BillingTransaction,
    TimescaleDBDailyBillingSummary,
)

from uuid import UUID
from turtle import up
from typing import Sequence
from decimal import Decimal
from datetime import datetime

from sqlalchemy import and_, func, text, select, update
from sqlalchemy.ext.asyncio import AsyncSession


bucket_map = {
    AggregatePeriod.DAILY: "day",
    AggregatePeriod.WEEKLY: "week",
    AggregatePeriod.MONTHLY: "month",
    AggregatePeriod.YEARLY: "year",
}


class TransactionRepository(Repository[BillingTransaction, UUID]):
    """Repository for BillingTransaction records.

    BillingTransaction stores only apikey_id. For project/org-level queries
    the service layer resolves project_id / org_id -> apikey_ids first, then
    passes the list to getByApiKeys / sumByApiKeysInPeriod.
    """

    def __init__(self):
        super().__init__(BillingTransaction, BillingTransaction.uuid)

    async def addTransaction(
        self,
        session: AsyncSession,
        transaction_id: UUID,
        apikey_id: int,
        project_id: int,
        org_id: str,
        amount: Decimal,
        details: dict,
        capture: bool = False,
    ) -> BillingTransaction:
        """Persist the final charge record (called during RELEASE)."""
        tx = BillingTransaction(
            uuid=transaction_id,
            apikey_id=apikey_id,
            project_id=project_id,
            organization_id=org_id,
            amount=amount,
            details=details,
            captured_at=func.now() if capture else None,
        )
        await self.add(session, tx)
        return tx

    async def captureTransaction(
        self,
        session: AsyncSession,
        transaction_id: UUID,
        real_amount: Decimal,
    ) -> BillingTransaction | None:
        """Update the transaction record with the real amount and mark as captured (called during CAPTURE)."""
        stmt = (
            update(BillingTransaction)
            .where(
                (BillingTransaction.uuid == transaction_id)
                & (
                    BillingTransaction.captured_at.is_(None)
                )  # only capture if not already captured
            )
            .values(
                amount=real_amount,  # update to real amount
                captured_at=func.now(),
            )
            .returning(BillingTransaction)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def getByApiKeys(
        self,
        session: AsyncSession,
        apikey_ids: list[int],
        org_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a set of API keys, newest first.

        Use for project-level or org-level queries: resolve
        project_id / org_id -> apikey_ids in the service layer first.
        """
        stmt = (
            select(BillingTransaction)
            .where(
                and_(
                    BillingTransaction.apikey_id.in_(apikey_ids),
                    BillingTransaction.organization_id == org_id,
                )
            )
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByOrganizations(
        self,
        session: AsyncSession,
        org_ids: list[str],
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for an organization, newest first."""
        stmt = (
            select(BillingTransaction)
            .where(BillingTransaction.organization_id.in_(org_ids))
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByProjects(
        self,
        session: AsyncSession,
        project_ids: list[int],
        org_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a project, newest first."""
        stmt = (
            select(BillingTransaction)
            .where(
                and_(
                    BillingTransaction.project_id.in_(project_ids),
                    BillingTransaction.organization_id == org_id,
                )
            )
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def sumByPeriodByApiKeys(
        self,
        session: AsyncSession,
        apikey_ids: list[int],
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReport]:
        """Sum the total amount for a set of API keys in a time period."""
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.apikey_id.in_(apikey_ids),
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    async def sumByPeriodByOrganizations(
        self,
        session: AsyncSession,
        org_ids: list[str],
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReport]:
        """Sum the total amount for an organization in a time period."""
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id.in_(org_ids),
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)

        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    async def sumByPeriodByProjects(
        self,
        session: AsyncSession,
        project_ids: list[int],
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReport]:
        """Sum the total amount for a project in a time period."""
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.project_id.in_(project_ids),
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]


if __name__ == "__main__":
    # For testing purposes only
    from src.shared.utils.uuid_utils import uuid7

    import asyncio

    async def test():
        async with getTimescaleSessionManager().get_session() as session:
            repo = TransactionRepository()
            await repo.addTransaction(
                session=session,
                transaction_id=uuid7(),
                apikey_id=1,
                project_id=1,
                org_id="org1",
                amount=Decimal("10.5"),
                details={"example": "data"},
            )
            await repo.addTransaction(
                session=session,
                transaction_id=uuid7(),
                apikey_id=2,
                project_id=1,
                org_id="org1",
                amount=Decimal("20.0"),
                details={"example": "data"},
            )
            await session.commit()
        async with getTimescaleSessionManager().get_session() as session:
            transactions = await repo.sumByPeriodByApiKeys(
                session=session,
                apikey_ids=[1, 2, 3],
                org_id="org1",
                start_time=datetime(2026, 1, 1),
                end_time=datetime(2026, 12, 31),
                period=AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            print(transactions)

    asyncio.run(test())
