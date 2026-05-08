from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses.response import ObjectResponse

from ..dtos import AddCreditRequest, CreditInfoResponse
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
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    credit_service: Annotated[CreditService, Depends(getCreditService)],
    body: Annotated[AddCreditRequest, Body()],
) -> ObjectResponse[CreditInfoResponse]:
    credits = await credit_service.addCredits(
        org_id=user_info["org_uuid"],
        amount_to_add=body.amount,
        description=body.description,
    )
    return ObjectResponse[CreditInfoResponse](
        data=CreditInfoResponse(amount=credits)
    )
