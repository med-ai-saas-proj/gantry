from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo

from ..dtos import SpendingLimitInfo, UpdateSpendingLimitRequest
from .router import billing_router
from ..factories import BillingService, getBillingService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends, APIRouter


@billing_router.put(
    "/spending-limits",
    description="Update spending limits for a specific invoice.",
)
async def update_spending_limits(
    invoice_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    body: Annotated[UpdateSpendingLimitRequest, Body()],
):
    pass


@billing_router.get(
    "/spending-limits",
    description="Get current spending limits for a project or organization.",
)
async def get_spending_limits(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    offset: int = 0,
    limit: int = 100,
) -> list[SpendingLimitInfo]:
    pass


@billing_router.get(
    "/spending-limits/{project_uid}",
    description="Get spending limit for a specific project.",
)
async def get_project_spending_limit(
    project_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> SpendingLimitInfo:
    pass
