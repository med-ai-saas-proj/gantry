from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses.response import PaginatedResponse

from ..dtos import (
    AddCreditRequest,
    CreditInfoResponse,
)
from .router import billing_router
from ..factories import TransactionService, getBillingTransactionService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends


@billing_router.post(
    "/credits",
    description="Add credits to an organization or project (e.g. from a promotion, refund, etc.).",
)
async def add_credits(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    body: Annotated[AddCreditRequest, Body()],
):
    pass


@billing_router.get(
    "/credits",
    description="List credits for an organization or project, with filters for status (e.g. 'active', 'used', 'expired').",
)
async def list_credits(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    status: str | None = None,  # e.g. "active", "used", "expired"
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[CreditInfoResponse]:
    pass


@billing_router.get(
    "/credits",
    description="List credits for an organization or project, with filters for status (e.g. 'active', 'used', 'expired').",
)
async def list_credits_for_admin(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    org_id: list[UUID] | None = None,  # filter by org_id for admin users
    status: str | None = None,  # e.g. "active", "used", "expired"
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[CreditInfoResponse]:
    pass
