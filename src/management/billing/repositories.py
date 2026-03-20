"""Billing repository layer."""

from src.db.repository import Repository

from .models import (
    SpendingLimitType,
    UsageAggregate,
    BillingTransaction,
    SpendingLimit
)

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import datetime

from sqlalchemy import and_, func, or_, true, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


class BillingTransactionRepository(Repository[BillingTransaction, UUID]):
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
        apikey_id: int,
        amount: Decimal,
        details: dict,
    ) -> BillingTransaction:
        """Persist the final charge record (called during RELEASE)."""
        tx = BillingTransaction(
            apikey_id=apikey_id,
            amount=amount,
            details=details,
        )
        await self.add(session, tx)
        return tx

    async def getByApiKey(
        self,
        session: AsyncSession,
        apikey_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a single API key, newest first."""
        stmt = (
            select(BillingTransaction)
            .where(BillingTransaction.apikey_id == apikey_id)
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByApiKeys(
        self,
        session: AsyncSession,
        apikey_ids: list[int],
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a set of API keys, newest first.

        Use for project-level or org-level queries: resolve
        project_id / org_id -> apikey_ids in the service layer first.
        """
        stmt = (
            select(BillingTransaction)
            .where(BillingTransaction.apikey_id.in_(apikey_ids))
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def sumByApiKeysInPeriod(
        self,
        session: AsyncSession,
        apikey_ids: list[int],
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """Sum committed transaction amounts over a time window.

        period_start is inclusive, period_end is exclusive.
        """
        stmt = select(func.sum(BillingTransaction.amount)).where(
            BillingTransaction.apikey_id.in_(apikey_ids),
            BillingTransaction.created_at >= period_start,
            BillingTransaction.created_at < period_end,
        )
        result = await session.execute(stmt)
        total = result.scalar()
        return total if total is not None else Decimal("0")


class UsageAggregateRepository:
    """Repository for UsageAggregate records."""

    async def getAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
    ) -> UsageAggregate | None:
        """Get an aggregate.

        Billing_period format: "YYYY-MM" (e.g., "2026-02").
        """
        stmt = (
            select(UsageAggregate)
            .where(
                UsageAggregate.project_id == project_id,
                UsageAggregate.billing_period == billing_period,
            )
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
    
    async def holdAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        org_id: str,
        billing_period: str,
        hold_amount: Decimal,
        project_limit: Decimal | None,
        org_limit: Decimal | None,
    ) -> Sequence[UsageAggregate] | None:
        """Upsert an aggregate row and atomically increment its total.

        - If the row doesn't exist yet: inserts it with total_amount = amount.
        - If it exists and is open: increments total_amount atomically.
        - If it exists but is finalized: DO NOTHING, returns None — the
          service layer should treat that as an error.

        Takes (project_id, billing_period) instead of aggregate_id so
        the caller doesn't need a prior getOrCreate round-trip.
        """
        if project_limit is not None and hold_amount > project_limit:
            return None
        if org_limit is not None and hold_amount > org_limit:
            return None

        stmt1 = (
            insert(UsageAggregate)
            .values(
                organization_id=org_id,
                project_id=project_id,
                billing_period=billing_period,
                total_amount=hold_amount,
                is_finalized=False,
            )
            .on_conflict_do_update(
                index_elements=["organization_id", "project_id", "billing_period"],
                set_={
                    "total_amount": UsageAggregate.total_amount + hold_amount,
                    "updated_at": func.now(),
                },
                where=and_(
                    UsageAggregate.is_finalized == False,
                    (UsageAggregate.total_amount + hold_amount <= project_limit)
                    if project_limit is not None
                    else true(),
                ),
            )
            .returning(UsageAggregate)
        )
        row1 = await session.execute(stmt1)
        stmt2 = (
            insert(UsageAggregate)
            .values(
                organization_id=org_id,
                billing_period=billing_period,
                total_amount=hold_amount,
                is_finalized=False,
            )
            .on_conflict_do_update(
                index_elements=["organization_id", "billing_period"],
                index_where=UsageAggregate.project_id.is_(None),
                set_={
                    "total_amount": UsageAggregate.total_amount + hold_amount,
                    "updated_at": func.now(),
                },
                where=and_(
                    UsageAggregate.is_finalized == False,
                    (UsageAggregate.total_amount + hold_amount <= org_limit)
                    if org_limit is not None
                    else true(),
                ),
            )
            .returning(UsageAggregate)
        )
        row2 = await session.execute(stmt2)
        agg1 = row1.scalar_one_or_none()
        agg2 = row2.scalar_one_or_none()
        if agg1 is None or agg2 is None:
            return None
        return [agg1, agg2]

    async def releaseAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        org_id: str,
        billing_period: str,
        delta_amount: Decimal,
    ) -> Sequence[UsageAggregate] | None:
        """Adjust the aggregate total by delta_amount (may be negative).

        delta = real_cost − hold_amount. Negative when the hold over-estimated
        (the common case).

        Returns None if the period was finalized between HOLD and RELEASE
        (month-end race).
        """
        stmt1 = (
            update(UsageAggregate)
            .where(
                UsageAggregate.project_id == project_id,
                UsageAggregate.billing_period == billing_period,
                UsageAggregate.is_finalized == False,
            )
            .values(
                total_amount=UsageAggregate.total_amount + delta_amount,
                updated_at=func.now(),
            )
            .returning(UsageAggregate)
        )
        result = await session.execute(stmt1)
        row1 = result.scalar_one_or_none()
        if row1 is None:
            return None
        
        stmt2 = (
            update(UsageAggregate)
            .where(
                UsageAggregate.organization_id == org_id,
                UsageAggregate.billing_period == billing_period,
                UsageAggregate.is_finalized == False,
            ).values(
                total_amount=UsageAggregate.total_amount + delta_amount,
                updated_at=func.now(),
            ).returning(UsageAggregate)
        )
        result2 = await session.execute(stmt2)
        row2 = result2.scalar_one_or_none()
        if row2 is None:
            return None
        return [row1, row2]

    async def finalize(
        self,
        session: AsyncSession,
        project_id: int,
        org_id: str,
        billing_period: str,
    ) -> Sequence[UsageAggregate] | None:
        """Mark an aggregate as finalized (immutable).

        Returns None if it was already finalized or not found.
        """
        stmt = (
            update(UsageAggregate)
            .where(
                UsageAggregate.organization_id == org_id, 
                or_(UsageAggregate.project_id.is_(None),
                UsageAggregate.project_id == project_id,
                    ),
                UsageAggregate.billing_period == billing_period,
                UsageAggregate.is_finalized == False,
            )
            .values(is_finalized=True, updated_at=func.now())
            .returning(UsageAggregate)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def getByProject(
        self,
        session: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[UsageAggregate]:
        """Get aggregates for a project, most recent period first."""
        stmt = (
            select(UsageAggregate)
            .where(UsageAggregate.project_id == project_id)
            .order_by(UsageAggregate.billing_period.desc())
        )
        if skip is not None:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def getByOrg(
        self,
        session: AsyncSession,
        org_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[UsageAggregate]:
        """Get aggregates for an organization, most recent period first."""
        stmt = (
            select(UsageAggregate)
            .where(UsageAggregate.organization_id == org_id)
            .order_by(UsageAggregate.billing_period.desc())
        )
        if skip is not None:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def getByProjectAndPeriod(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
    ) -> UsageAggregate | None:
        """Get the aggregate for a specific project and billing period."""
        stmt = (
            select(UsageAggregate)
            .where(
                UsageAggregate.project_id == project_id,
                UsageAggregate.billing_period == billing_period,
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class SpendingLimitRepository(
    Repository[SpendingLimit, int]
):
    """Repository forspending limits."""

    def __init__(self):
        super().__init__(
            SpendingLimit, SpendingLimit.id
        )

    async def get(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int,
        limit_type: SpendingLimitType
    ) -> Sequence[SpendingLimit]:
        """Get the spending limit record for an organization."""
        stmt = (
            select(SpendingLimit)
            .where(
                (SpendingLimit.organization_id == org_id)
                & (
                    (SpendingLimit.project_id == project_id)
                    | SpendingLimit.project_id.is_(None)  # global default
                )
                & (SpendingLimit.limit_type == limit_type)
            )
        )
        return await self.selectMany(session, stmt)

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int | None,
        monthly_limit: Decimal | None,
        daily_limit: Decimal | None,
    ) -> SpendingLimit | None:
        """Create or update the spending limits for an organization."""
        if project_id is not None:
            stmt = (
                insert(SpendingLimit)
                .values(
                    organization_id=org_id,
                    project_id=project_id,
                    monthly_limit=monthly_limit,
                    daily_limit=daily_limit,
                )
                .on_conflict_do_update(
                    index_elements=["organization_id", "project_id"],
                    set_={
                        "monthly_limit": monthly_limit,
                        "daily_limit": daily_limit,
                        "updated_at": func.now(),
                    },
                )
                .returning(SpendingLimit)
            )
        else:
            stmt = (
                insert(SpendingLimit)
                .values(
                    organization_id=org_id,
                    monthly_limit=monthly_limit,
                    daily_limit=daily_limit,
                )
                .on_conflict_do_update(
                    index_elements=["organization_id"],
                    index_where=SpendingLimit.project_id.is_(None),
                    set_={
                        "monthly_limit": monthly_limit,
                        "daily_limit": daily_limit,
                        "updated_at": func.now(),
                    },
                )
                .returning(SpendingLimit)
            )
        result = await session.execute(stmt)
        return result.scalars().first()

