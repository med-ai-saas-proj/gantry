from src.management.billing.dtos import (
    TransactionInfoResponse,
)
from src.management.auth.entities import UserInfo
from src.management.api_keys.entities import ApiKeyInfo
from src.management.auth.dependencies import getUserInfo
from src.management.api_keys.dependencies import requiredPermissions

from ..dtos import PostRequest, CaptureRequest
from .router import billing_router
from ..factories import TransactionService, getBillingTransactionService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Body, Depends


@billing_router.post("/")
async def post(
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[PostRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> UUID:
    return (
        await billing_service.post(
            org_id=apikey_info["org_id"],
            project_id=apikey_info["project_id"],
            api_key_id=apikey_info["api_key_id"],
            req=body,
        )
    ).unwrap()


@billing_router.post("/capture/{hold_uuid}")
async def capture(
    hold_uuid: UUID,
    apikey_info: Annotated[
        ApiKeyInfo, Depends(requiredPermissions(["billing:write"]))
    ],
    body: Annotated[CaptureRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> bool:
    return (
        await billing_service.capture(
            org_id=apikey_info["org_id"],
            project_id=apikey_info["project_id"],
            api_key_id=apikey_info["api_key_id"],
            transaction_uid=hold_uuid,
            real_amount=body.real_amount,
        )
    ).unwrap()


@billing_router.get(
    "/transactions",
    description="List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination.",
)
async def list_transactions(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    project_uid: list[UUID]
    | None = None,  # filter by project_uid or whole organization
    start_date: datetime | None = None,  # ISO date string
    end_date: datetime | None = None,  # ISO date string
    limit: int = 100,
    offset: int = 0,
) -> list[TransactionInfoResponse]:
    pass


@billing_router.get(
    "/transactions/{transaction_uid}",
    description="Get details for a specific transaction, including amount, date, associated project, etc.",
)
async def get_transaction_details(
    transaction_uid: UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> TransactionInfoResponse:
    pass
