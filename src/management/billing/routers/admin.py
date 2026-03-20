from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions

from ..dtos import (
    CreditInfo,
    BillingPing,
    HoldRequest,
    ScaledAmount,
    ReleaseRequest,
    AddCreditRequest,
)
from .router import billing_router
from ..factories import BillingService, getBillingService

import enum
from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Body, Depends, APIRouter


@billing_router.post(
    "/credits",
    description="Add credits to an organization or project (e.g. from a promotion, refund, etc.).",
)
async def add_credits(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    body: Annotated[AddCreditRequest, Body()],
):
    pass


@billing_router.get(
    "/credits",
    description="List credits for an organization or project, with filters for status (e.g. 'active', 'used', 'expired').",
)
async def list_credits(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:read"]))
    ],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    project_uid: UUID
    | None = None,  # filter by project_uid or whole organization
    status: str | None = None,  # e.g. "active", "used", "expired"
    limit: int = 100,
    offset: int = 0,
) -> list[CreditInfo]:
    pass
