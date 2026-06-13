from gantry.shared.custom_types.error_exception import (
    ExternalAPIError,
    NotImplementedError,
)

from ..dtos import (
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from .billing_source_provider import BillingSourceProviderInterface

from types import CoroutineType
from typing import Any

from stripe import StripeError, StripeClient
from pyrusult import Ok, Err
from stripe.params import CustomerUpdateParams


class StripeBillingSourceProviderInterface(BillingSourceProviderInterface):
    def __init__(self, stripe_client: StripeClient):
        self.client = stripe_client

    async def _wrap(self, coro: CoroutineType):
        try:
            result = await coro
            return Ok(result)
        except StripeError as e:
            return Err(
                ExternalAPIError(
                    message=f"Stripe API error: {e.user_message or str(e)}",
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

    async def createCustomer(self, req: AddBillingSourceRequest):
        return await self._wrap(self._createCustomer(req))

    async def _createCustomer(self, req: AddBillingSourceRequest):
        return (
            await self.client.v1.customers.create_async(
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
            )
        ).id

    async def _updateCustomer(
        self, provider_id: str, req: UpdateBillingSourceRequest
    ):
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

        return (
            await self.client.v1.customers.update_async(provider_id, payload)
        ).to_dict()

    async def updateCustomer(
        self, provider_id: str, req: UpdateBillingSourceRequest
    ):
        return await self._wrap(self._updateCustomer(provider_id, req))

    async def _createSetupIntent(self, provider_id: str):
        return (
            await self.client.v1.setup_intents.create_async(
                {
                    "customer": provider_id,
                    "usage": "off_session",
                    "payment_method_types": ["card", "us_bank_account"],
                }
            )
        ).to_dict()

    async def createSetupIntent(self, provider_id: str):
        return await self._wrap(self._createSetupIntent(provider_id))

    async def _listRequiredActionSetupIntents(self, provider_id: str):
        res = await self.client.v1.setup_intents.list_async(
            {"customer": provider_id}
        )
        return [i.to_dict() for i in res.data if i.status == "requires_action"]

    async def listRequiredActionSetupIntents(self, provider_id: str):
        return await self._wrap(
            self._listRequiredActionSetupIntents(provider_id)
        )

    async def _cancelSetupIntent(self, setup_intent_id: str):
        return (
            await self.client.v1.setup_intents.cancel_async(setup_intent_id)
        ).to_dict()

    async def cancelSetupIntent(self, setup_intent_id: str):
        return await self._wrap(self._cancelSetupIntent(setup_intent_id))

    async def _listPaymentMethods(self, provider_id: str):
        res = await self.client.v1.payment_methods.list_async(
            {"customer": provider_id}
        )
        return [pm.to_dict() for pm in res.data]

    async def listPaymentMethods(self, provider_id: str):
        return await self._wrap(self._listPaymentMethods(provider_id))

    async def _getPaymentMethod(self, payment_method_id: str):
        return (
            await self.client.v1.payment_methods.retrieve_async(
                payment_method_id
            )
        ).to_dict()

    async def getPaymentMethod(self, payment_method_id: str):
        return await self._wrap(self._getPaymentMethod(payment_method_id))

    async def _detachPaymentMethod(self, payment_method_id: str):
        return (
            await self.client.v1.payment_methods.detach_async(payment_method_id)
        ).to_dict()

    async def detachPaymentMethod(self, payment_method_id: str):
        return await self._wrap(self._detachPaymentMethod(payment_method_id))

    async def _getCustomer(self, provider_id: str):
        return (
            await self.client.v1.customers.retrieve_async(provider_id)
        ).to_dict()

    async def getCustomer(
        self, provider_id: str
    ) -> (
        Ok[Any, ExternalAPIError | NotImplementedError]
        | Err[dict, ExternalAPIError | NotImplementedError]
    ):
        return await self._wrap(self._getCustomer(provider_id))
