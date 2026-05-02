from gantry.management.api_key import ApiKeyInfo, getApiKeyInfo

from ..dtos import PostRequest, CaptureRequest
from ..factories import getBillingTransactionService
from .internal_router import internal_billing_router
from ..services.transaction_services import TransactionService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Header, Depends


@internal_billing_router.post("/")
async def post(
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
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


@internal_billing_router.post("/{transaction_uid}/capture")
async def capture(
    transaction_uid: UUID,
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
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
