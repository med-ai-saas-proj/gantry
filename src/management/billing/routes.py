"""Billing API routes."""

from .dtos import BillingPing, ScaledAmount
from .dependencies import BillingContext, get_billing_context
from .factories import BillingService, getBillingService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends, APIRouter
from pydantic import BaseModel


class HoldRequest(BaseModel):
    amount: ScaledAmount
    details: dict = {}


class ReleaseRequest(BaseModel):
    real_amount: ScaledAmount


billing_router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)


@billing_router.post("/hold")
async def hold(
    ctx: Annotated[BillingContext, Depends(get_billing_context)],
    body: Annotated[HoldRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> UUID:
    ping: BillingPing = {
        "organization_id": ctx["organization_id"],
        "project_id": ctx["project_id"],
        "apikey_id": ctx["apikey_id"],
        "org_project_ids": ctx["org_project_ids"],
        "amount": body.amount,
        "details": body.details,
    }
    return (await billing_service.hold(ping)).unwrap()


@billing_router.post("/release/{hold_uuid}")
async def release(
    hold_uuid: UUID,
    ctx: Annotated[BillingContext, Depends(get_billing_context)],
    body: Annotated[ReleaseRequest, Body()],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
) -> bool:
    return (await billing_service.release(hold_uuid, body.real_amount)).unwrap()
