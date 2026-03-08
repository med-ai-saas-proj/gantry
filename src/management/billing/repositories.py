"""Billing repository layer."""

from src.db.repository import Repository

from .models import (
    MonthlyAggregate,
    BillingTransaction,
    ProjectSpendingLimit,
    OrganizationSpendingLimit,
)

from uuid import UUID
from decimal import Decimal
from datetime import datetime
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


class BillingTransactionRepository(Repository[BillingTransaction, UUID]):
    """Repository for BillingTransaction records.

    BillingTransaction stores only apikey_id. For project/org-level queries
    the service layer resolves project_id / org_id -> apikey_ids first, then
    passes the list to getByApiKeys / sumByApiKeysInPeriod.

    The HOLD step (Redis) is handled entirely in the service layer.
    This repository only handles the Postgres INSERT that happens during RELEASE.
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

    async def getOrCreate(
        self,
        session: AsyncSession,
        project_id: str,
        billing_period: str,
    ) -> MonthlyAggregate | None:
        """Get an aggregate or create it if it doesn't exist.

        Billing_period format: "YYYY-MM" (e.g., "2026-02").
        """
        stmt = (
            insert(MonthlyAggregate)
            .values(
                project_id=project_id,
                billing_period=billing_period,
                total_amount=Decimal("0"),
                is_finalized=False,
            )
            .on_conflict_do_nothing(
                index_elements=["project_id", "billing_period"]
            )
        )
        await session.execute(stmt)

        fetch_stmt = (
            select(MonthlyAggregate)
            .where(
                MonthlyAggregate.project_id == project_id,
                MonthlyAggregate.billing_period == billing_period,
            )
            .limit(1)
        )
        return await self.selectOne(session, fetch_stmt)

    async def addToAggregate(
        self,
        session: AsyncSession,
        aggregate_id: int,
        amount: Decimal,
    ) -> MonthlyAggregate | None:
        """Increment an aggregate's total by amount.

        Single UPDATE avoids lost-update races. Returns None if the
        aggregate was already finalized or not found, the service layer
        should treat that as an error.
        """
        stmt = (
            update(MonthlyAggregate)
            .where(
                MonthlyAggregate.id == aggregate_id,
                MonthlyAggregate.is_finalized == False,
            )
            .values(
                total_amount=MonthlyAggregate.total_amount + amount,
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
        project_id: str,
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
        project_id: str,
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


class OrganizationSpendingLimitRepository(
    Repository[OrganizationSpendingLimit, int]
):
    """Repository for organization-level spending limits."""

    def __init__(self):
        super().__init__(
            OrganizationSpendingLimit, OrganizationSpendingLimit.id
        )

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
        project_id: str,
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
        project_id: str,
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
