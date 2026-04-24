from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import (
    AddCreditRequest,
    CreditInfoResponse,
    CreditTransactionInfoResponse,
)
from ..factories import getCreditService
from .internal_router import internal_billing_router
from ..services.credit_service import CreditService

from typing import Annotated

from fastapi import Body, Depends


@internal_billing_router.post(
    "/credits",
    tags=["admin"],
    description="Add credits to an organization or project (e.g. from a promotion, refund, etc.).",
)
async def add_credits(
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
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


@internal_billing_router.get(
    "/credits/{org_id}/available",
    description="Get available credits for the organization",
)
async def get_available_credits(
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    org_id: str,
    credit_service: Annotated[CreditService, Depends(getCreditService)],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.getAvailableCredits(org_id=org_id)
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )


@internal_billing_router.get(
    "/credits/{org_id}/transactions",
    description="List credit transactions (e.g. when credits were added from promotions, refunds, or used to offset an invoice).",
)
async def list_credit_transactions(
    # TODO: use admin dependency here
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
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
