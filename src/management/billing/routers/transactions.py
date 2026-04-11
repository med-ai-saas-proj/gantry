from src.management.auth.entities import UserInfo
from src.management.api_keys.entities import ApiKeyInfo
from src.management.auth.dependencies import getUserInfo
from src.management.api_keys.dependencies import getApiKeyInfo
from src.shared.custom_types.responses.response import (
    ObjectResponse,
    PaginatedResponse,
)

from ..dtos import PostRequest, CaptureRequest, TransactionInfoResponse
from .router import billing_router
from ..factories import TransactionService, getBillingTransactionService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Body, Query, Header, Depends


@billing_router.post("/")
async def post(
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo())],
    body: Annotated[PostRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    idempotency_key: str | None = Header(None),
) -> UUID:
    return (
        await billing_service.post(
            idempotency_key=idempotency_key,
            org_id=apikey_info["org_id"],
            project_id=apikey_info["project_id"],
            api_key_id=apikey_info["api_key_id"],
            req=body,
        )
    ).unwrap()


@billing_router.post("/{transaction_uid}/capture")
async def capture(
    transaction_uid: UUID,
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo())],
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
            transaction_uid=transaction_uid,
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
    project_uids: list[UUID] | None = Query(
        None
    ),  # filter by project_uid or whole organization
    start_date: datetime | None = None,  # ISO date string
    end_date: datetime | None = None,  # ISO date string
    limit: int = 100,
    offset: int = 0,
) -> PaginatedResponse[TransactionInfoResponse]:
    res, total = (
        await billing_service.getTransactions(
            org_id=user_info["org_id"],
            project_uids=project_uids,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
    ).unwrap()
    return PaginatedResponse[TransactionInfoResponse](
        data=res, total=total, offset=offset, limit=limit
    )


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
) -> ObjectResponse[TransactionInfoResponse]:
    res = (
        await billing_service.getTransactionById(
            org_id=user_info["org_id"], transaction_uid=transaction_uid
        )
    ).unwrap()
    return ObjectResponse[TransactionInfoResponse](data=res)
