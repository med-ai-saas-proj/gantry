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
    apikey_info: Annotated[ApiKeyInfo, Depends(getApiKeyInfo)],
    body: Annotated[PostRequest, Body()],
    billing_service: Annotated[
        TransactionService, Depends(getBillingTransactionService)
    ],
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
    idempotency_key: str | None = Header(None),
) -> UUID:
    internal_ids = (
        await apikey_service.getApiKeyInternalIds(apikey_info["api_key_uuid"])
    ).unwrap()
    return (
        await billing_service.post(
            idempotency_key=idempotency_key,
            org_id=apikey_info["organization_uuid"],
            project_id=internal_ids["project_id"],
            api_key_id=internal_ids["api_key_id"],
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
    apikey_service: Annotated[ApiKeyService, Depends(getApiKeyService)],
) -> bool:
    internal_ids = (
        await apikey_service.getApiKeyInternalIds(apikey_info["api_key_uuid"])
    ).unwrap()
    return (
        await billing_service.capture(
            org_id=apikey_info["organization_uuid"],
            project_id=internal_ids["project_id"],
            api_key_id=internal_ids["api_key_id"],
            transaction_uid=transaction_uid,
            real_amount=body.real_amount,
        )
    ).unwrap()
