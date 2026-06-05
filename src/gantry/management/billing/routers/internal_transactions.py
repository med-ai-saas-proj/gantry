from gantry.management.api_key import ApiKeyInfo, getApiKeyInfo
from gantry.management.api_key.factories import ApiKeyService, getApiKeyService

from ..dtos import PostRequest, CaptureRequest
from ..factories import getBillingTransactionService
from .internal_router import internal_billing_router
from ..services.transaction_services import TransactionService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Header, Depends


@internal_billing_router.post("/")
async def post(
    body: Annotated[PostRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    idempotency_key: str | None = Header(None),
) -> UUID:
    return (
        await billing_service.post(
            idempotency_key=idempotency_key,
            req=body,
        )
    ).unwrap()


@internal_billing_router.post("/{transaction_uid}/capture")
async def capture(
    transaction_uid: UUID,
    body: Annotated[CaptureRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
) -> bool:
    return (
        await billing_service.capture(
            transaction_uid=transaction_uid,
            real_amount=body.real_amount,
        )
    ).unwrap()
