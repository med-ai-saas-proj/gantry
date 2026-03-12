"""Billing repository layer."""

from src.db.repository import Repository

from .models import (
    MonthlyAggregate,
    BillingTransaction,
    ProjectSpendingLimit,
    OrganizationSpendingLimit,
)

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import datetime

from sqlalchemy import and_, func, select, true, update
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


class MonthlyAggregateRepository(Repository[MonthlyAggregate, int]):
    """Repository for MonthlyAggregate records."""

    def __init__(self):
        super().__init__(MonthlyAggregate, MonthlyAggregate.id)

    async def getAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
    ) -> MonthlyAggregate | None:
        """Get an aggregate.

        Billing_period format: "YYYY-MM" (e.g., "2026-02").
        """
        stmt = (
            select(MonthlyAggregate)
            .where(
                MonthlyAggregate.project_id == project_id,
                MonthlyAggregate.billing_period == billing_period,
            )
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def sumOrgTotal(
        self,
        session: AsyncSession,
        org_project_ids: list[int],
        billing_period: str,
    ) -> Decimal:
        """Sum total_amount across all open aggregates for the org's projects.

        Used to enforce the org-level monthly spending cap.
        Finalized rows are included — finalization doesn't reduce the org total.
        """
        stmt = select(
            func.coalesce(func.sum(MonthlyAggregate.total_amount), Decimal("0"))
        ).where(
            MonthlyAggregate.project_id.in_(org_project_ids),
            MonthlyAggregate.billing_period == billing_period,
        )
        result = await session.execute(stmt)
        return result.scalar() or Decimal("0")

    async def holdAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
        hold_amount: Decimal,
        project_limit: Decimal | None,
    ) -> MonthlyAggregate | None:
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

        limit_where = (
            MonthlyAggregate.total_amount + hold_amount <= project_limit
            if project_limit is not None
            else true()
        )

        stmt = (
            insert(MonthlyAggregate)
            .values(
                project_id=project_id,
                billing_period=billing_period,
                total_amount=hold_amount,
                is_finalized=False,
            )
            .on_conflict_do_update(
                index_elements=["project_id", "billing_period"],
                set_={
                    "total_amount": MonthlyAggregate.total_amount + hold_amount,
                    "updated_at": func.now(),
                },
                where=and_(
                    MonthlyAggregate.is_finalized == False,
                    limit_where,
                ),
            )
            .returning(MonthlyAggregate)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def releaseAggregate(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
        delta_amount: Decimal,
    ) -> MonthlyAggregate | None:
        """Adjust the aggregate total by delta_amount (may be negative).

        delta = real_cost − hold_amount. Negative when the hold over-estimated
        (the common case).

        Returns None if the period was finalized between HOLD and RELEASE
        (month-end race).
        """
        stmt = (
            update(MonthlyAggregate)
            .where(
                MonthlyAggregate.project_id == project_id,
                MonthlyAggregate.billing_period == billing_period,
                MonthlyAggregate.is_finalized == False,
            )
            .values(
                total_amount=MonthlyAggregate.total_amount + delta_amount,
                updated_at=func.now(),
            )
            .returning(MonthlyAggregate)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def finalize(
        self,
        session: AsyncSession,
        aggregate_id: int,
    ) -> MonthlyAggregate | None:
        """Mark an aggregate as finalized (immutable).

        Returns None if it was already finalized or not found.
        """
        stmt = (
            update(MonthlyAggregate)
            .where(
                MonthlyAggregate.id == aggregate_id,
                MonthlyAggregate.is_finalized == False,
            )
            .values(is_finalized=True, updated_at=func.now())
            .returning(MonthlyAggregate)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def getByProject(
        self,
        session: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[MonthlyAggregate]:
        """Get aggregates for a project, most recent period first."""
        stmt = (
            select(MonthlyAggregate)
            .where(MonthlyAggregate.project_id == project_id)
            .order_by(MonthlyAggregate.billing_period.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByProjectAndPeriod(
        self,
        session: AsyncSession,
        project_id: int,
        billing_period: str,
    ) -> MonthlyAggregate | None:
        """Get the aggregate for a specific project and billing period."""
        stmt = (
            select(MonthlyAggregate)
            .where(
                MonthlyAggregate.project_id == project_id,
                MonthlyAggregate.billing_period == billing_period,
            )
            .limit(1)
        )
        return await self.selectOne(session, stmt)


class OrganizationSpendingLimitRepository(Repository[OrganizationSpendingLimit, int]):
    """Repository for organization-level spending limits."""

    def __init__(self):
        super().__init__(OrganizationSpendingLimit, OrganizationSpendingLimit.id)

    async def getForOrg(
        self,
        session: AsyncSession,
        org_id: str,
    ) -> OrganizationSpendingLimit | None:
        """Get the spending limit record for an organization."""
        stmt = (
            select(OrganizationSpendingLimit)
            .where(OrganizationSpendingLimit.organization_id == org_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        monthly_limit: Decimal | None,
        daily_limit: Decimal | None,
    ) -> OrganizationSpendingLimit | None:
        """Create or update the spending limits for an organization."""
        stmt = (
            insert(OrganizationSpendingLimit)
            .values(
                organization_id=org_id,
                monthly_limit=monthly_limit,
                daily_limit=daily_limit,
            )
            .on_conflict_do_update(
                index_elements=["organization_id"],
                set_={
                    "monthly_limit": monthly_limit,
                    "daily_limit": daily_limit,
                    "updated_at": func.now(),
                },
            )
            .returning(OrganizationSpendingLimit)
        )
        result = await session.execute(stmt)
        return result.scalars().first()


class ProjectSpendingLimitRepository(Repository[ProjectSpendingLimit, int]):
    """Repository for project-level spending limits."""

    def __init__(self):
        super().__init__(ProjectSpendingLimit, ProjectSpendingLimit.id)

    async def getForProject(
        self,
        session: AsyncSession,
        project_id: int,
    ) -> ProjectSpendingLimit | None:
        """Get the spending limit record for a project."""
        stmt = (
            select(ProjectSpendingLimit)
            .where(ProjectSpendingLimit.project_id == project_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def upsert(
        self,
        session: AsyncSession,
        project_id: int,
        monthly_limit: Decimal | None,
        daily_limit: Decimal | None,
    ) -> ProjectSpendingLimit | None:
        """Create or update the spending limits for a project."""
        stmt = (
            insert(ProjectSpendingLimit)
            .values(
                project_id=project_id,
                monthly_limit=monthly_limit,
                daily_limit=daily_limit,
            )
            .on_conflict_do_update(
                index_elements=["project_id"],
                set_={
                    "monthly_limit": monthly_limit,
                    "daily_limit": daily_limit,
                    "updated_at": func.now(),
                },
            )
            .returning(ProjectSpendingLimit)
        )
        result = await session.execute(stmt)
        return result.scalars().first()
