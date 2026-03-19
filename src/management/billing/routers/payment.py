
from datetime import datetime
import enum

from src.management.api_keys.dependencies import requiredPermissions
from src.management.api_keys.entities import ApiKeyInfo
from src.management.auth.dependencies import getUserInfo
from src.management.auth.entities import UserInfo

from ..dtos import BillingPing, HoldRequest, ReleaseRequest
from ..factories import BillingService, getBillingService

from uuid import UUID
from typing import Annotated

from fastapi import Body, Depends

from .router import billing_router

@billing_router.post(
    "/sources/{provider}",
    description="Add a billing source (e.g. Stripe customer) for an organization."
)
async def add_billing_source(
    provider: str, # e.g. "stripe", "paypal", etc.
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    source_details: dict = Body(...), # e.g. {"customer_id": "cus_12345"} for Stripe
):
    pass

class BillingSourceProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    # Add more providers as needed (e.g. "braintree", "square", etc.)

@billing_router.get(
    "/sources",
    description="List billing sources for an organization."
)
async def list_billing_sources(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.put(
    "/sources/{provider}",
    description="Update a billing source (e.g. change default payment method, update billing address, etc.)."
)
async def update_billing_source(
    provider: BillingSourceProvider,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    source_details: dict = Body(...), # e.g. {"default_payment_method": "pm_12345"} for Stripe
):
    pass

@billing_router.delete(
    "/sources/{provider}",
    description="Remove a billing source from an organization."
)
async def delete_billing_source(
    provider: BillingSourceProvider,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.post(
    "/sources/{provider}/setup_intents",
    description="Create a setup intent for a billing source."
)
async def create_setup_intent(
    provider: BillingSourceProvider,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.delete(
    "/sources/{provider}/payment_method/{payment_method_id}",
    description="Remove a payment method from a billing source."
)
async def delete_payment_method(
    provider: BillingSourceProvider,
    payment_method_id: str, # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.get(
    "/sources/{provider}/payment_methods",
    description="List payment methods for a billing source."
)
async def list_payment_methods(
    provider: BillingSourceProvider,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass


@billing_router.get(
    "/sources/{provider}/payment_methods/{payment_method_id}",
    description="Get details for a specific payment method."
)
async def get_payment_method_details(
    provider: BillingSourceProvider,
    payment_method_id: str, # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.get(
    "/sources/{provider}/setup_intents/pending",
    description="List pending setup intent for a billing source (used to verify payment method after linking)"
)
async def list_pending_setup_intents(
    provider: BillingSourceProvider,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass

@billing_router.delete(
    "/sources/{provider}/setup_intents/{setup_intent_id}",
    description="Cancel a pending setup intent for a billing source."
)
async def cancel_setup_intent(
    provider: BillingSourceProvider,
    setup_intent_id: str,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
):
    pass
