from src.management.billing.dtos import (
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from src.shared.custom_types.error_exception import ExternalAPIError

from .billing_source_provider import BillingSourceProviderInterface

import asyncio

from stripe import StripeError, StripeClient
from safe_result import Ok, Err
from stripe.params import CustomerUpdateParams


class StripeBillingSourceProviderInterface(BillingSourceProviderInterface):
    def __init__(self, stripe_client: StripeClient):
        self.client = stripe_client

    def _wrap(self, fn):
        try:
            return Ok(fn())
        except StripeError as e:
            return Err(
                ExternalAPIError(
                    message=f"Stripe API error: {e.user_message}",
                    from_exception=e,
                )
            )
        except Exception as e:
            return Err(
                ExternalAPIError(
                    message=f"Unexpected error: {str(e)}",
                    from_exception=e,
                )
            )

    async def _async_wrap(self, fn):
        return await asyncio.to_thread(self._wrap, fn)

    async def createCustomer(self, req: AddBillingSourceRequest):
        return await self._async_wrap(
            lambda: (
                self.client.v1.customers.create(
                    {
                        "name": req.name,
                        "email": req.email,
                        "phone": req.phone,
                        "address": {
                            "line1": req.address.line1,
                            "line2": req.address.line2,
                            "city": req.address.city,
                            "state": req.address.state,
                            "postal_code": req.address.postal_code,
                            "country": req.address.country,
                        },
                    }
                ).id
            )
        )

    async def deleteCustomer(self, provider_id: str):
        return await self._async_wrap(
            lambda: self.client.v1.customers.delete(provider_id)
        )

    async def updateCustomer(
        self, provider_id: str, req: UpdateBillingSourceRequest
    ):
        def fn():
            payload: CustomerUpdateParams = {}
            if req.new_email:
                payload["email"] = req.new_email
            if req.new_phone:
                payload["phone"] = req.new_phone
            if req.new_address:
                payload["address"] = {
                    "line1": req.new_address.line1,
                    "line2": req.new_address.line2,
                    "city": req.new_address.city,
                    "state": req.new_address.state,
                    "postal_code": req.new_address.postal_code,
                    "country": req.new_address.country,
                }
            self.client.v1.customers.update(provider_id, payload)

        return await self._async_wrap(fn)

    async def createSetupIntent(self, provider_id: str):
        return await self._async_wrap(
            lambda: self.client.v1.setup_intents.create(
                {
                    "customer": provider_id,
                    "usage": "off_session",
                    "payment_method_types": ["card", "us_bank_account"],
                }
            )
        )

    async def listRequiredActionSetupIntents(self, provider_id: str):
        def fn():
            res = self.client.v1.setup_intents.list({"customer": provider_id})
            return [i for i in res.data if i.status == "requires_action"]

        return await self._async_wrap(fn)

    async def cancelSetupIntent(self, setup_intent_id: str):
        return await self._async_wrap(
            lambda: self.client.v1.setup_intents.cancel(setup_intent_id)
        )

    async def listPaymentMethods(self, provider_id: str):
        return await self._async_wrap(
            lambda: (
                self.client.v1.payment_methods.list(
                    {"customer": provider_id}
                ).data
            )
        )

    async def getPaymentMethod(self, payment_method_id: str):
        return await self._async_wrap(
            lambda: self.client.v1.payment_methods.retrieve(payment_method_id)
        )

    async def detachPaymentMethod(self, payment_method_id: str):
        return await self._async_wrap(
            lambda: self.client.v1.payment_methods.detach(payment_method_id)
        )
