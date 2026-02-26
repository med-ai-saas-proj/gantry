from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.billing.entities import BillingTransaction, MonthlyBill


class BillingRepository:
    """Repository for billing-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

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
        # For now, return empty dict - can be enhanced later
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
