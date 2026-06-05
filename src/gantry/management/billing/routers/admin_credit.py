from gantry.management.auth.entities import UserInfo, AdminInfo
from gantry.management.auth.dependencies import getAdminInfo
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import (
    AddCreditRequest,
    CreditInfoResponse,
    CreditTransactionInfoResponse,
)
from .router import billing_router
from ..factories import getCreditService
from ..services.credit_service import CreditService

from typing import Annotated

from fastapi import Body, Depends


@billing_router.post(
    "/admin/credits",
    tags=["admin"],
    description="Add credits to an organization or project (e.g. from a promotion, refund, etc.).",
)
async def add_credits(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
    body: Annotated[AddCreditRequest, Body()],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.addCredits(
        org_id=body.org_id,
        amount_to_add=body.amount,
        description=body.description,
    )
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )


@billing_router.get(
    "/admin/credits/{org_id}/available",
    description="Get available credits for the organization",
    tags=["admin"],
)
async def get_available_credits(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    org_id: str,
    credit_service: Annotated[CreditService, Depends(getCreditService)],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.getAvailableCredits(org_id=org_id)
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )


@billing_router.get(
    "/admin/credits/{org_id}/transactions",
    description="List credit transactions (e.g. when credits were added from promotions, refunds, or used to offset an invoice).",
    tags=["admin"],
)
async def list_credit_transactions(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
    org_id: str,
    offset: int = 0,
    limit: int = 100,
) -> PaginatedResponse[CreditTransactionInfoResponse]:
    transactions, total = await credit_service.getCreditTransactions(
        org_id=org_id,
        offset=offset,
        limit=limit,
    )
    return PaginatedResponse(
        data=transactions,
        total=total,
        limit=limit,
        offset=offset,
    )
