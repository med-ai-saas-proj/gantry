from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.billing.entities import (
    BillingTransaction,
    MonthlyBill,
    BillingSource,
    BillingSourceType,
    BillingSourceStatus,
)
from src.service.billing.dtos import (
    BillingChargeRequest,
    BillingChargeResponse,
    MonthlyBillSummary,
    ProjectBillingSummary,
    CreateBillingSourceRequest,
    BillingSourceResponse,
    UpdateBillingSourceRequest,
    AddCreditsRequest,
)
from src.service.billing.repositories import BillingRepository


class InsufficientCreditsError(Exception):
    """Raised when there are insufficient credits for a transaction."""

    pass


class NoBillingSourceError(Exception):
    """Raised when no active billing source is found."""

    pass


class BillingService:
    """Service for managing billing transactions and monthly aggregations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = BillingRepository(session)

    # ============ Billing Sources ============

    async def create_billing_source(
        self, request: CreateBillingSourceRequest
    ) -> BillingSourceResponse:
        """Create a new billing source."""
        source = BillingSource(
            organization_id=request.organization_id,
            project_id=request.project_id,
            source_type=request.source_type,
            name=request.name,
            description=request.description,
            priority=request.priority,
            status=BillingSourceStatus.ACTIVE,
        )

        # Handle credits
        if request.source_type == BillingSourceType.CREDITS:
            if request.initial_credits is None:
                raise ValueError("initial_credits required for CREDITS source type")
            source.credit_balance = request.initial_credits
            source.initial_credits = request.initial_credits

        # Handle external integrations
        elif request.source_type in [
            BillingSourceType.STRIPE,
            BillingSourceType.PAYPAL,
        ]:
            source.external_id = request.external_id
            source.external_metadata = request.external_metadata

        saved_source = await self.repository.create_billing_source(source)

        return BillingSourceResponse(
            id=saved_source.id,
            organization_id=saved_source.organization_id,
            project_id=saved_source.project_id,
            source_type=saved_source.source_type,
            status=saved_source.status,
            name=saved_source.name,
            description=saved_source.description,
            credit_balance=saved_source.credit_balance,
            initial_credits=saved_source.initial_credits,
            priority=saved_source.priority,
            created_at=saved_source.created_at,
            updated_at=saved_source.updated_at,
        )

    async def list_billing_sources(
        self,
        organization_id: UUID,
        project_id: UUID | None = None,
        status: BillingSourceStatus | None = None,
    ) -> list[BillingSourceResponse]:
        """List billing sources."""
        sources = await self.repository.list_billing_sources(
            organization_id, project_id, status
        )

        return [
            BillingSourceResponse(
                id=s.id,
                organization_id=s.organization_id,
                project_id=s.project_id,
                source_type=s.source_type,
                status=s.status,
                name=s.name,
                description=s.description,
                credit_balance=s.credit_balance,
                initial_credits=s.initial_credits,
                priority=s.priority,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sources
        ]

    async def update_billing_source(
        self, source_id: UUID, request: UpdateBillingSourceRequest
    ) -> BillingSourceResponse:
        """Update a billing source."""
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.status is not None:
            updates["status"] = request.status
        if request.priority is not None:
            updates["priority"] = request.priority

        updated_source = await self.repository.update_billing_source(source_id, updates)

        if not updated_source:
            raise ValueError(f"Billing source {source_id} not found")

        return BillingSourceResponse(
            id=updated_source.id,
            organization_id=updated_source.organization_id,
            project_id=updated_source.project_id,
            source_type=updated_source.source_type,
            status=updated_source.status,
            name=updated_source.name,
            description=updated_source.description,
            credit_balance=updated_source.credit_balance,
            initial_credits=updated_source.initial_credits,
            priority=updated_source.priority,
            created_at=updated_source.created_at,
            updated_at=updated_source.updated_at,
        )

    async def add_credits(
        self, source_id: UUID, request: AddCreditsRequest
    ) -> BillingSourceResponse:
        """Add credits to a billing source."""
        updated_source = await self.repository.add_credits(source_id, request.amount)

        if not updated_source:
            raise ValueError(
                f"Billing source {source_id} not found or not a credits source"
            )

        return BillingSourceResponse(
            id=updated_source.id,
            organization_id=updated_source.organization_id,
            project_id=updated_source.project_id,
            source_type=updated_source.source_type,
            status=updated_source.status,
            name=updated_source.name,
            description=updated_source.description,
            credit_balance=updated_source.credit_balance,
            initial_credits=updated_source.initial_credits,
            priority=updated_source.priority,
            created_at=updated_source.created_at,
            updated_at=updated_source.updated_at,
        )

    # ============ Transactions ============

    async def charge(
        self,
        request: BillingChargeRequest,
    ) -> BillingChargeResponse:
        """
        Record a billing charge for an API call.
        Automatically selects and uses appropriate billing source.
        """
        # Get active billing source
        billing_source = await self.repository.get_active_billing_source(
            request.organization_id,
            request.project_id,
        )

        if not billing_source:
            raise NoBillingSourceError(
                f"No active billing source found for project {request.project_id}"
            )

        # Handle credits deduction
        if billing_source.source_type == BillingSourceType.CREDITS:
            success = await self.repository.deduct_credits(
                billing_source.id,
                request.amount_charged,
            )
            if not success:
                raise InsufficientCreditsError(
                    f"Insufficient credits in billing source {billing_source.id}"
                )

        # TODO: Handle 3rd party payment processing here when implemented
        # elif billing_source.source_type == BillingSourceType.STRIPE:
        #     await self._process_stripe_payment(...)

        # Create transaction record
        transaction = BillingTransaction(
            organization_id=request.organization_id,
            project_id=request.project_id,
            billing_source_id=billing_source.id,
            amount_charged=request.amount_charged,
            details=request.details,
            llm_usages=request.llm_usages,
            timestamp=datetime.now(timezone.utc),
        )

        saved_transaction = await self.repository.create_transaction(transaction)

        return BillingChargeResponse(
            transaction_id=saved_transaction.id,
            organization_id=saved_transaction.organization_id,
            project_id=saved_transaction.project_id,
            amount_charged=saved_transaction.amount_charged,
            billing_source_id=saved_transaction.billing_source_id,
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

        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)

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
                source_breakdown=existing_bill.source_breakdown,
                llm_usage_summary=existing_bill.llm_usage_summary,
                period_start=existing_bill.period_start,
                period_end=existing_bill.period_end,
                generated_at=existing_bill.generated_at,
            )

        summary = await self.repository.get_project_summary(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )

        source_breakdown = await self.repository.get_source_breakdown(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
        )

        monthly_bill = MonthlyBill(
            organization_id=organization_id,
            project_id=project_id,
            year=year,
            month=month,
            total_amount=summary.get("total_amount") or Decimal("0.00"),
            transaction_count=summary.get("transaction_count") or 0,
            source_breakdown=source_breakdown,
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
            source_breakdown=saved_bill.source_breakdown,
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
                source_breakdown=bill.source_breakdown,
                llm_usage_summary=bill.llm_usage_summary,
                period_start=bill.period_start,
                period_end=bill.period_end,
                generated_at=bill.generated_at,
            )
            for bill in bills
        ]
