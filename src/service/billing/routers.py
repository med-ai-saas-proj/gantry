from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from huggingface_hub import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.factories import getSessionManager
from src.service.billing.dtos import (
    BillingChargeRequest,
    BillingChargeResponse,
    MonthlyBillSummary,
    ProjectBillingSummary,
)
from src.service.billing.services import BillingService

router = APIRouter(prefix="/bill", tags=["Billing"])


@router.post("/charge", response_model=BillingChargeResponse)
async def charge_api_call(
    request: BillingChargeRequest,
    session: AsyncSession = Depends(getSessionManager().get_session),
) -> BillingChargeResponse:
    """
    Record a billing charge for an API call.
    This endpoint should be called by internal services when completing an API request.
    """
    service = BillingService(session)
    return await service.charge(request)


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
