from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.factories import getSessionManager
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
from src.service.billing.entities import BillingSourceStatus
from src.service.billing.services import (
    BillingService,
    InsufficientCreditsError,
    NoBillingSourceError,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ============ Billing Sources ============


@router.post("/sources", response_model=BillingSourceResponse, status_code=201)
async def create_billing_source(
    request: CreateBillingSourceRequest,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> BillingSourceResponse:
    """Create a new billing source (credits or future 3rd party integration)."""
    service = BillingService(session)
    return await service.create_billing_source(request)


@router.get("/sources", response_model=list[BillingSourceResponse])
async def list_billing_sources(
    organization_id: UUID,
    project_id: UUID | None = None,
    status: BillingSourceStatus | None = None,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> list[BillingSourceResponse]:
    """List billing sources for an organization or project."""
    service = BillingService(session)
    return await service.list_billing_sources(organization_id, project_id, status)


@router.patch("/sources/{source_id}", response_model=BillingSourceResponse)
async def update_billing_source(
    source_id: UUID,
    request: UpdateBillingSourceRequest,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> BillingSourceResponse:
    """Update a billing source."""
    service = BillingService(session)
    try:
        return await service.update_billing_source(source_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sources/{source_id}/credits", response_model=BillingSourceResponse)
async def add_credits(
    source_id: UUID,
    request: AddCreditsRequest,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> BillingSourceResponse:
    """Add credits to a billing source."""
    service = BillingService(session)
    try:
        return await service.add_credits(source_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ Transactions ============


@router.post("/charge", response_model=BillingChargeResponse)
async def charge_api_call(
    request: BillingChargeRequest,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> BillingChargeResponse:
    """
    Record a billing charge for an API call.
    Automatically selects and charges the appropriate billing source.
    """
    service = BillingService(session)
    try:
        return await service.charge(request)
    except NoBillingSourceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))  # 402 Payment Required


# ============ Summaries ============


@router.get("/project/{project_id}/current", response_model=ProjectBillingSummary)
async def get_current_month_project_summary(
    project_id: UUID,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> ProjectBillingSummary:
    """Get current month billing summary for a project."""
    service = BillingService(session)
    return await service.get_project_current_month_summary(project_id)


@router.get(
    "/organization/{organization_id}/current",
    response_model=list[ProjectBillingSummary],
)
async def get_current_month_organization_summary(
    organization_id: UUID,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> list[ProjectBillingSummary]:
    """Get current month billing summary for all projects in an organization."""
    service = BillingService(session)
    return await service.get_organization_current_month_summary(organization_id)


@router.post("/aggregate", response_model=MonthlyBillSummary)
async def aggregate_monthly_bill(
    organization_id: UUID,
    project_id: UUID,
    year: int,
    month: int,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> MonthlyBillSummary:
    """
    Aggregate and finalize monthly bill for a project.
    Should be called at the end of each month.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    service = BillingService(session)
    return await service.aggregate_monthly_bill(
        organization_id=organization_id,
        project_id=project_id,
        year=year,
        month=month,
    )


@router.get(
    "/organization/{organization_id}/bills", response_model=list[MonthlyBillSummary]
)
async def list_monthly_bills(
    organization_id: UUID,
    project_id: UUID | None = None,
    limit: int = 12,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> list[MonthlyBillSummary]:
    """List historical monthly bills for an organization or project."""
    service = BillingService(session)
    return await service.list_monthly_bills(
        organization_id=organization_id,
        project_id=project_id,
        limit=limit,
    )
