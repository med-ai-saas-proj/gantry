from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.service.billing.entities import (
    BillingTransaction,
    MonthlyBill,
    BillingSource,
    BillingSourceStatus,
)


class BillingRepository:
    """Repository for billing-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============ Billing Sources ============

    async def create_billing_source(self, source: BillingSource) -> BillingSource:
        """Create a new billing source."""
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        return source

    async def get_billing_source(self, source_id: UUID) -> Optional[BillingSource]:
        """Get a billing source by ID."""
        stmt = select(BillingSource).where(BillingSource.id == source_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_billing_sources(
        self,
        organization_id: UUID,
        project_id: UUID | None = None,
        status: BillingSourceStatus | None = None,
    ) -> list[BillingSource]:
        """List billing sources for an organization/project."""
        stmt = select(BillingSource).where(
            BillingSource.organization_id == organization_id
        )

        if project_id is not None:
            stmt = stmt.where(BillingSource.project_id == project_id)

        if status:
            stmt = stmt.where(BillingSource.status == status)

        stmt = stmt.order_by(BillingSource.priority.desc(), BillingSource.created_at)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_billing_source(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> Optional[BillingSource]:
        """
        Get the active billing source with highest priority for a project.
        Checks project-level first, then falls back to organization-level.
        """
        # First try project-level sources
        stmt = (
            select(BillingSource)
            .where(
                BillingSource.organization_id == organization_id,
                BillingSource.project_id == project_id,
                BillingSource.status == BillingSourceStatus.ACTIVE,
            )
            .order_by(BillingSource.priority.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        source = result.scalar_one_or_none()

        if source:
            return source

        # Fall back to organization-level sources
        stmt = (
            select(BillingSource)
            .where(
                BillingSource.organization_id == organization_id,
                BillingSource.project_id.is_(None),
                BillingSource.status == BillingSourceStatus.ACTIVE,
            )
            .order_by(BillingSource.priority.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_billing_source(
        self,
        source_id: UUID,
        updates: dict[str, Any],
    ) -> Optional[BillingSource]:
        """Update a billing source."""
        updates["updated_at"] = datetime.utcnow()

        stmt = (
            update(BillingSource)
            .where(BillingSource.id == source_id)
            .values(**updates)
            .returning(BillingSource)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def deduct_credits(
        self,
        source_id: UUID,
        amount: Decimal,
    ) -> bool:
        """
        Deduct credits from a billing source.
        Returns True if successful, False if insufficient credits.
        """
        source = await self.get_billing_source(source_id)

        if not source or source.credit_balance is None:
            return False

        if source.credit_balance < amount:
            # Mark as depleted
            await self.update_billing_source(
                source_id, {"status": BillingSourceStatus.DEPLETED}
            )
            return False

        new_balance = source.credit_balance - amount

        # Update balance and status if depleted
        updates: dict[str, Any] = {"credit_balance": new_balance}
        if new_balance <= Decimal("0"):
            updates["status"] = BillingSourceStatus.DEPLETED

        await self.update_billing_source(source_id, updates)
        return True

    async def add_credits(
        self,
        source_id: UUID,
        amount: Decimal,
    ) -> Optional[BillingSource]:
        """Add credits to a billing source."""
        source = await self.get_billing_source(source_id)

        if not source or source.credit_balance is None:
            return None

        new_balance = source.credit_balance + amount

        updates: dict[str, Any] = {
            "credit_balance": new_balance,
            "initial_credits": (
                source.initial_credits + amount if source.initial_credits else amount
            ),
        }

        # Reactivate if was depleted
        if source.status == BillingSourceStatus.DEPLETED:
            updates["status"] = BillingSourceStatus.ACTIVE

        return await self.update_billing_source(source_id, updates)

    # ============ Transactions ============

    async def create_transaction(
        self, transaction: BillingTransaction
    ) -> BillingTransaction:
        """Create a new billing transaction."""
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def get_project_summary(
        self,
        project_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Get billing summary for a project within a date range.

        Returns:
            Dictionary with total_amount, transaction_count, and llm_usage_summary
        """
        # Get aggregate data
        stmt = select(
            func.sum(BillingTransaction.amount_charged).label("total_amount"),
            func.count(BillingTransaction.id).label("transaction_count"),
        ).where(
            BillingTransaction.project_id == project_id,
            BillingTransaction.timestamp >= start_date,
            BillingTransaction.timestamp < end_date,
        )

        result = await self.session.execute(stmt)
        row = result.one()

        # TODO: Get LLM usage summary (would need more complex aggregation)
        llm_usage_summary: dict[str, Any] = {}

        return {
            "total_amount": row.total_amount,
            "transaction_count": row.transaction_count,
            "llm_usage_summary": llm_usage_summary,
        }

    async def get_organization_summary(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """
        Get billing summary for all projects in an organization.

        Returns:
            List of dictionaries with project_id, total_amount, transaction_count
        """
        stmt = (
            select(
                BillingTransaction.project_id,
                func.sum(BillingTransaction.amount_charged).label("total_amount"),
                func.count(BillingTransaction.id).label("transaction_count"),
            )
            .where(
                BillingTransaction.organization_id == organization_id,
                BillingTransaction.timestamp >= start_date,
                BillingTransaction.timestamp < end_date,
            )
            .group_by(BillingTransaction.project_id)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "project_id": row.project_id,
                "total_amount": row.total_amount,
                "transaction_count": row.transaction_count,
                "llm_usage_summary": {},
            }
            for row in rows
        ]

    async def get_source_breakdown(
        self,
        project_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """Get breakdown of charges by billing source."""
        stmt = (
            select(
                BillingTransaction.billing_source_id,
                func.sum(BillingTransaction.amount_charged).label("amount"),
                func.count(BillingTransaction.id).label("count"),
            )
            .where(
                BillingTransaction.project_id == project_id,
                BillingTransaction.timestamp >= start_date,
                BillingTransaction.timestamp < end_date,
            )
            .group_by(BillingTransaction.billing_source_id)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return {
            str(row.billing_source_id): {
                "amount": row.amount,
                "count": row.count,
            }
            for row in rows
            if row.billing_source_id
        }

    # ============ Monthly Bills ============

    async def create_monthly_bill(self, bill: MonthlyBill) -> MonthlyBill:
        """Create a new monthly bill record."""
        self.session.add(bill)
        await self.session.commit()
        await self.session.refresh(bill)
        return bill

    async def get_monthly_bill(
        self,
        organization_id: UUID,
        project_id: UUID,
        year: int,
        month: int,
    ) -> Optional[MonthlyBill]:
        """Get a specific monthly bill if it exists."""
        stmt = select(MonthlyBill).where(
            MonthlyBill.organization_id == organization_id,
            MonthlyBill.project_id == project_id,
            MonthlyBill.year == year,
            MonthlyBill.month == month,
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_monthly_bills(
        self,
        organization_id: UUID,
        project_id: Optional[UUID] = None,
        limit: int = 12,
    ) -> list[MonthlyBill]:
        """List monthly bills ordered by date (newest first)."""
        stmt = (
            select(MonthlyBill)
            .where(MonthlyBill.organization_id == organization_id)
            .order_by(MonthlyBill.year.desc(), MonthlyBill.month.desc())
            .limit(limit)
        )

        if project_id:
            stmt = stmt.where(MonthlyBill.project_id == project_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
