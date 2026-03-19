"""Billing API routes."""

from src.management.api_keys.dependencies import requiredPermissions
from src.management.api_keys.entities import ApiKeyInfo

from ..dtos import BillingPing, HoldRequest, ReleaseRequest
from ..factories import BillingService, getBillingService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends

from .router import billing_router


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
        description="Directly create a transaction without a hold. For use cases where the cost is known upfront and there's no need to reserve funds in advance (e.g. one-time charges, fixed-price services, etc.)."
        )
async def direct_charge(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[HoldRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

