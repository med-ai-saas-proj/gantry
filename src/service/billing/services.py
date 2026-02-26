from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.billing.entities import BillingTransaction, MonthlyBill
from src.service.billing.dtos import (
    BillingChargeRequest,
    BillingChargeResponse,
    MonthlyBillSummary,
    ProjectBillingSummary,
)
from src.service.billing.repositories import BillingRepository


class BillingService:
    """Service for managing billing transactions and monthly aggregations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = BillingRepository(session)

    async def charge(
        self,
        request: BillingChargeRequest,
    ) -> BillingChargeResponse:
        """
        Record a billing charge for an API call.
        This should be called when the API response is sent to the client.

        Args:
            request: Billing charge request containing organization, project, and usage details

        Returns:
            BillingChargeResponse with transaction details
        """
        # Create transaction record
        transaction = BillingTransaction(
            organization_id=request.organization_id,
            project_id=request.project_id,
            amount_charged=request.amount_charged,
            details=request.details,
            llm_usages=request.llm_usages,
            timestamp=datetime.now(timezone.utc),
        )

        # Save transaction
        saved_transaction = await self.repository.create_transaction(transaction)

        return BillingChargeResponse(
            transaction_id=saved_transaction.id,
            organization_id=saved_transaction.organization_id,
            project_id=saved_transaction.project_id,
            amount_charged=saved_transaction.amount_charged,
            timestamp=saved_transaction.timestamp,
        )

    async def get_project_current_month_summary(
        self,
        project_id: UUID,
    ) -> ProjectBillingSummary:
        """
        Get current month billing summary for a project.

        Args:
            project_id: Project UUID

        Returns:
            ProjectBillingSummary with current month's charges
        """
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        result = await self.repository.get_project_summary(
            project_id=project_id,
            start_date=start_of_month,
            end_date=now,
        )

        return ProjectBillingSummary(
            project_id=project_id,
            period_start=start_of_month,
            period_end=now,
            total_amount=result.get("total_amount") or Decimal("0.00"),
            transaction_count=result.get("transaction_count") or 0,
            llm_usage_summary=result.get("llm_usage_summary") or {},
        )

    async def get_organization_current_month_summary(
        self,
        organization_id: UUID,
    ) -> list[ProjectBillingSummary]:
        """
        Get current month billing summary for all projects in an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of ProjectBillingSummary for each project
        """
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        results = await self.repository.get_organization_summary(
            organization_id=organization_id,
            start_date=start_of_month,
            end_date=now,
        )

        return [
            ProjectBillingSummary(
                project_id=result["project_id"],
                period_start=start_of_month,
                period_end=now,
                total_amount=result.get("total_amount") or Decimal("0.00"),
                transaction_count=result.get("transaction_count") or 0,
                llm_usage_summary=result.get("llm_usage_summary") or {},
            )
            for result in results
        ]

    async def aggregate_monthly_bill(
        self,
        organization_id: UUID,
        project_id: UUID,
        year: int,
        month: int,
    ) -> MonthlyBillSummary:
        """
        Aggregate and finalize monthly bill for a project.
        This should be called at the end of each month.

        Args:
            organization_id: Organization UUID
            project_id: Project UUID
            year: Year (e.g., 2026)
            month: Month (1-12)

        Returns:
            MonthlyBillSummary with aggregated data
        """
        # Calculate month boundaries (calendar month)
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)

        # Calculate next month for end date
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Check if bill already exists
        existing_bill = await self.repository.get_monthly_bill(
            organization_id=organization_id,
            project_id=project_id,
            year=year,
            month=month,
        )

        if existing_bill:
            return MonthlyBillSummary(
                bill_id=existing_bill.id,
                organization_id=existing_bill.organization_id,
                project_id=existing_bill.project_id,
                year=existing_bill.year,
                month=existing_bill.month,
                total_amount=existing_bill.total_amount,
                transaction_count=existing_bill.transaction_count,
                llm_usage_summary=existing_bill.llm_usage_summary,
                period_start=existing_bill.period_start,
                period_end=existing_bill.period_end,
                generated_at=existing_bill.generated_at,
            )

        # Aggregate transactions for the month
        summary = await self.repository.get_project_summary(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Create monthly bill record
        monthly_bill = MonthlyBill(
            organization_id=organization_id,
            project_id=project_id,
            year=year,
            month=month,
            total_amount=summary.get("total_amount") or Decimal("0.00"),
            transaction_count=summary.get("transaction_count") or 0,
            llm_usage_summary=summary.get("llm_usage_summary") or {},
            period_start=start_date,
            period_end=end_date,
            generated_at=datetime.now(timezone.utc),
        )

        saved_bill = await self.repository.create_monthly_bill(monthly_bill)

        return MonthlyBillSummary(
            bill_id=saved_bill.id,
            organization_id=saved_bill.organization_id,
            project_id=saved_bill.project_id,
            year=saved_bill.year,
            month=saved_bill.month,
            total_amount=saved_bill.total_amount,
            transaction_count=saved_bill.transaction_count,
            llm_usage_summary=saved_bill.llm_usage_summary,
            period_start=saved_bill.period_start,
            period_end=saved_bill.period_end,
            generated_at=saved_bill.generated_at,
        )

    async def list_monthly_bills(
        self,
        organization_id: UUID,
        project_id: Optional[UUID] = None,
        limit: int = 12,
    ) -> list[MonthlyBillSummary]:
        """
        List monthly bills for an organization or specific project.

        Args:
            organization_id: Organization UUID
            project_id: Optional project UUID filter
            limit: Maximum number of bills to return

        Returns:
            List of MonthlyBillSummary ordered by date (newest first)
        """
        bills = await self.repository.list_monthly_bills(
            organization_id=organization_id,
            project_id=project_id,
            limit=limit,
        )

        return [
            MonthlyBillSummary(
                bill_id=bill.id,
                organization_id=bill.organization_id,
                project_id=bill.project_id,
                year=bill.year,
                month=bill.month,
                total_amount=bill.total_amount,
                transaction_count=bill.transaction_count,
                llm_usage_summary=bill.llm_usage_summary,
                period_start=bill.period_start,
                period_end=bill.period_end,
                generated_at=bill.generated_at,
            )
            for bill in bills
        ]
