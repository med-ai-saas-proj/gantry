from src.management.billing.dtos import (
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.management.billing.services.billing_source_service import (
    BillingSourceService,
)

from .router import billing_router
from ..models import BillingSourceProvider
from ..factories import (
    TransactionService,
    getBillingSourceService,
    getBillingTransactionService,
)

import uuid
from typing import Annotated

from fastapi import Body, Depends


@billing_router.post(
    "/sources",
    description="Add a billing source (e.g. Stripe customer) for an organization.",
)
async def add_billing_source(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
    req: Annotated[AddBillingSourceRequest, Body()],
):
    res = await billing_source_service.addBillingSource(
        org_id=user_info["org_id"], req=req
    )
    return res.unwrap()


@billing_router.get(
    "/sources", description="List billing sources for an organization."
)
async def list_billing_sources(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
    providers: list[BillingSourceProvider] | None,
):
    res = await billing_source_service.listBillingSources(
        org_id=user_info["org_id"], providers=providers
    )
    return res.unwrap()


@billing_router.put(
    "/sources/{billing_source_uid}",
    description="Update a billing source (e.g. change default payment method, update billing address, etc.).",
)
async def update_billing_source(
    billing_source_uid: uuid.UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
    req: Annotated[UpdateBillingSourceRequest, Body()],
):
    res = await billing_source_service.updateBillingSource(
        org_id=user_info["org_id"],
        billing_source_uid=billing_source_uid,
        update_fields=req,
    )
    return res.unwrap()


@billing_router.delete(
    "/sources/{billing_source_uid}",
    description="Remove a billing source from an organization.",
)
async def delete_billing_source(
    billing_source_uid: uuid.UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.deleteBillingSource(
        org_id=user_info["org_id"],
        billing_source_uid=billing_source_uid,
    )
    return res.unwrap()


@billing_router.post(
    "/sources/{billing_source_uid}/setup_intents",
    description="Create a setup intent for a billing source.",
)
async def create_setup_intent(
    billing_source_uid: uuid.UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.createSetupIntent(
        user_info["org_id"], billing_source_uid
    )
    return res.unwrap()


@billing_router.delete(
    "/sources/{billing_source_uid}/payment_method/{payment_method_id}",
    description="Remove a payment method from a billing source.",
)
async def delete_payment_method(
    billing_source_uid: uuid.UUID,
    payment_method_id: str,  # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.deletePaymentMethod(
        user_info["org_id"], billing_source_uid, payment_method_id
    )
    return res.unwrap()


@billing_router.get(
    "/sources/{billing_source_uid}/payment_methods",
    description="List payment methods for a billing source.",
)
async def list_payment_methods(
    billing_source_uid: uuid.UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.listPaymentMethods(
        user_info["org_id"], billing_source_uid
    )
    return res.unwrap()


@billing_router.get(
    "/sources/{billing_source_uid}/payment_methods/{payment_method_id}",
    description="Get details for a specific payment method.",
)
async def get_payment_method_details(
    billing_source_uid: uuid.UUID,
    payment_method_id: str,  # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.getPaymentMethodDetails(
        user_info["org_id"], billing_source_uid, payment_method_id
    )
    return res.unwrap()


@billing_router.get(
    "/sources/{billing_source_uid}/setup_intents/required_actions",
    description="List setup intents that require user action for a billing source (used to verify payment method after linking)",
)
async def list_required_action_setup_intents(
    billing_source_uid: uuid.UUID,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.listRequiredActionSetupIntents(
        user_info["org_id"], billing_source_uid
    )
    return res.unwrap()


@billing_router.delete(
    "/sources/{billing_source_uid}/setup_intents/{setup_intent_id}",
    description="Cancel a pending setup intent for a billing source.",
)
async def cancel_setup_intent(
    billing_source_uid: uuid.UUID,
    setup_intent_id: str,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.cancelSetupIntent(
        user_info["org_id"], billing_source_uid, setup_intent_id
    )
    return res.unwrap()
