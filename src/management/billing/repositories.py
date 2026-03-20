"""Billing repository layer."""

from src.db.repository import Repository

from .models import SpendingLimit, SpendingLimitType, BillingTransaction

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import datetime

from sqlalchemy import or_, and_, func, true, select, update
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


class SpendingLimitRepository(Repository[SpendingLimit, int]):
    """Repository forspending limits."""

    def __init__(self):
        super().__init__(SpendingLimit, SpendingLimit.id)

    async def get(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int,
        limit_type: SpendingLimitType,
    ) -> Sequence[SpendingLimit]:
        """Get the spending limit record for an organization."""
        stmt = select(SpendingLimit).where(
            (SpendingLimit.organization_id == org_id)
            & (
                (SpendingLimit.project_id == project_id)
                | SpendingLimit.project_id.is_(None)  # global default
            )
            & (SpendingLimit.limit_type == limit_type)
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
