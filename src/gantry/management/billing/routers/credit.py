from gantry.management.auth.roles import ManagementRole
from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import requireRole
from gantry.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import (
    CreditInfoResponse,
    CreditTransactionInfoResponse,
)
from .router import billing_router
from ..factories import getCreditService
from ..services.credit_service import CreditService

import re
from typing import Annotated

from fastapi import Depends


@billing_router.get(
    "/credits/available",
    description="Get available credits for the organization",
)
async def get_available_credits(
    user_info: Annotated[
        UserInfo, Depends(requireRole(ManagementRole.BILLING_MANAGE))
    ],
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
    user_info: Annotated[
        UserInfo, Depends(requireRole(ManagementRole.BILLING_MANAGE))
    ],
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
