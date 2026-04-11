from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.shared.custom_types.responses.response import (
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
    "/credits",
    description="Add credits to an organization or project (e.g. from a promotion, refund, etc.).",
)
async def add_credits(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
    body: Annotated[AddCreditRequest, Body()],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.addCredits(
        org_id=user_info["org_id"],
        amount_to_add=body.amount,
        description=body.description,
    )
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )


@billing_router.get(
    "/credits",
    description="Get available credits for the organization",
)
async def get_available_credits(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.getAvailableCredits(
        org_id=user_info["org_id"]
    )
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )


@billing_router.get(
    "/credits/transactions",
    description="List credit transactions (e.g. when credits were added from promotions, refunds, or used to offset an invoice).",
)
async def list_credit_transactions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
    offset: int = 0,
    limit: int = 100,
) -> PaginatedResponse[CreditTransactionInfoResponse]:
    transactions, total = await credit_service.getCreditTransactions(
        org_id=user_info["org_id"],
        offset=offset,
        limit=limit,
    )
    return PaginatedResponse(
        data=transactions,
        total=total,
        limit=limit,
        offset=offset,
    )
