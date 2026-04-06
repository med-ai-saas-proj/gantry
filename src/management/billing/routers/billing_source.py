from src.management.billing.dtos import (
    BillingSourceResponse,
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
    BillingSourceDetailResponse,
)
from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.shared.custom_types.responses.response import (
    ObjectResponse,
)
from src.management.billing.services.billing_source_service import (
    BillingSourceService,
)

from .router import billing_router
from ..factories import (
    getBillingSourceService,
)

import uuid
from typing import Annotated

from fastapi import Body, Depends


@billing_router.post(
    "/sources",
    description="Create a new billing source for an organization.",
)
async def create_billing_source(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
    req: Annotated[AddBillingSourceRequest, Body()],
) -> ObjectResponse[BillingSourceResponse]:
    res = await billing_source_service.createBillingSource(
        org_id=user_info["org_id"], req=req
    )
    return ObjectResponse[BillingSourceResponse](data=res.unwrap())


@billing_router.get(
    "/sources", description="Get billing sources info for an organization."
)
async def billing_source_info(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
) -> ObjectResponse[BillingSourceDetailResponse]:
    res = await billing_source_service.getBillingSource(
        org_id=user_info["org_id"]
    )
    return ObjectResponse[BillingSourceDetailResponse](data=res.unwrap())


@billing_router.put(
    "/sources",
    description="Update a billing source (e.g. change default payment method, update billing address, etc.).",
)
async def update_billing_source(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
    req: Annotated[UpdateBillingSourceRequest, Body()],
):
    res = await billing_source_service.updateBillingSource(
        org_id=user_info["org_id"],
        update_fields=req,
    )
    res.unwrap()


@billing_router.post(
    "/sources/setup_intents",
    description="Create a setup intent for a billing source.",
)
async def create_setup_intent(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.createSetupIntent(user_info["org_id"])
    return res.unwrap()


@billing_router.delete(
    "/sources/payment_method/{payment_method_id}",
    description="Remove a payment method from a billing source.",
)
async def delete_payment_method(
    payment_method_id: str,  # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.deletePaymentMethod(
        user_info["org_id"], payment_method_id
    )
    res.unwrap()


@billing_router.get(
    "/sources/payment_methods",
    description="List payment methods for a billing source.",
)
async def list_payment_methods(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.listPaymentMethods(user_info["org_id"])
    return res.unwrap()


@billing_router.get(
    "/sources/payment_methods/{payment_method_id}",
    description="Get details for a specific payment method.",
)
async def get_payment_method_details(
    payment_method_id: str,  # e.g. "pm_12345" for Stripe
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.getPaymentMethodDetails(
        user_info["org_id"], payment_method_id
    )
    return res.unwrap()


@billing_router.get(
    "/sources/setup_intents/required_actions",
    description="List setup intents that require user action for a billing source (used to verify payment method after linking)",
)
async def list_required_action_setup_intents(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.listRequiredActionSetupIntents(
        user_info["org_id"],
    )
    return res.unwrap()


@billing_router.delete(
    "/sources/setup_intents/{setup_intent_id}",
    description="Cancel a pending setup intent for a billing source.",
)
async def cancel_setup_intent(
    setup_intent_id: str,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_source_service: Annotated[
        BillingSourceService, Depends(getBillingSourceService)
    ],
):
    res = await billing_source_service.cancelSetupIntent(
        user_info["org_id"], setup_intent_id
    )
    res.unwrap()
