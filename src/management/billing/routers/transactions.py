from src.management.billing.dtos import (
    TransactionInfo,
)
from src.management.auth.entities import UserInfo
from src.management.api_keys.entities import ApiKeyInfo
from src.management.auth.dependencies import getUserInfo
from src.management.api_keys.dependencies import requiredPermissions

from ..dtos import BillingPing, HoldRequest, ReleaseRequest
from .router import billing_router
from ..factories import BillingService, getBillingService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Body, Depends


@billing_router.post("/hold")
async def hold(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[HoldRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> UUID:
    ping: BillingPing = {
        "organization_id": apikey_info["org_id"],
        "project_id": apikey_info["project_id"],
        "apikey_id": apikey_info["api_key_id"],
        "amount": body.amount,
        "details": body.details,
    }
    return (await billing_service.hold(ping)).unwrap()


@billing_router.post("/release/{hold_uuid}")
async def release(
    hold_uuid: UUID,
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[ReleaseRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> bool:
    return (await billing_service.release(hold_uuid, body.real_amount)).unwrap()


@billing_router.post(
    "/",
    description="Directly create a transaction without a hold. For use cases where the cost is known upfront and there's no need to reserve funds in advance (e.g. one-time charges, fixed-price services, etc.).",
)
async def direct_charge(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[HoldRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass


@billing_router.get(
    "/transactions",
    description="List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination.",
)
async def list_transactions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    start_date: datetime | None = None,  # ISO date string
    end_date: datetime | None = None,  # ISO date string
    limit: int = 100,
    offset: int = 0,
) -> list[TransactionInfo]:
    pass


@billing_router.get(
    "/transactions/{transaction_uid}",
    description="Get details for a specific transaction, including amount, date, associated project, etc.",
)
async def get_transaction_details(
    transaction_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> TransactionInfo:
    pass
