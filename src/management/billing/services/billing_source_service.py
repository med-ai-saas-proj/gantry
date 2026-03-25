from src.db.session import AsyncSessionManager
from src.management.billing.dtos import (
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from src.shared.custom_types.error_exception import (
    ExternalAPIError,
    RecoverableError,
    InvalidEnumValueError,
)

from ..models import BillingSource, BillingSourceState, BillingSourceProvider
from ..repositories.billing_source_repo import BillingSourceRepo

import uuid
import asyncio
from typing import Sequence

from stripe import StripeError, StripeClient
from safe_result import Ok, Err, Result
from stripe.params import CustomerUpdateParams


class BillingSourceNotFoundError(RecoverableError):
    status = 404
    code = "billing_source_not_found"
    title = "Billing Source Not Found"
    detail = "The specified billing source was not found for the organization."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class BillingSourceService:
    def __init__(
        self,
        billing_source_repo: BillingSourceRepo,
        session_manager: AsyncSessionManager,
        stripe_client: StripeClient,
    ) -> None:
        self.billing_source_repo = billing_source_repo
        self.session_manager = session_manager
        self.stripe_client = stripe_client

    async def addBillingSource(
        self, org_id: str, req: AddBillingSourceRequest
    ) -> Result[
        BillingSource,
        InvalidEnumValueError | NotImplementedError | ExternalAPIError,
    ]:
        """Add a billing source (e.g. Stripe customer) for an organization."""
        if req.provider == BillingSourceProvider.STRIPE:
            return await self.addStripeBillingSource(org_id, req)
        elif req.provider == BillingSourceProvider.PAYPAL:
            return Err(NotImplementedError())
        else:
            return Err(InvalidEnumValueError())

    async def addStripeBillingSource(
        self, org_id: str, req: AddBillingSourceRequest
    ) -> Result[BillingSource, ExternalAPIError]:
        async with self.session_manager.get_session() as session:
            billing_source = BillingSource(
                organization_id=org_id,
                source_type=BillingSourceProvider.STRIPE,
                status=BillingSourceState.PENDING,
                provider_id="",  # Will be updated later when we get the Stripe customer ID
            )
            await self.billing_source_repo.add(session, billing_source)
            await session.commit()

        stripe_api_call_res = await asyncio.to_thread(
            self._createStripeCustomer, req
        )
        if isinstance(stripe_api_call_res, Err):
            return Err(stripe_api_call_res.error)
        stripe_customer_id = stripe_api_call_res.value

        async with self.session_manager.get_session() as session:
            updated_billing_source = (
                await self.billing_source_repo.fillProviderInfo(
                    session=session,
                    billing_source_id=billing_source.id,
                    provider_id=stripe_customer_id,
                )
            )
            session.expunge_all()
            await session.commit()

        return Ok(updated_billing_source)

    async def listBillingSources(
        self,
        org_id: str,
        providers: list[BillingSourceProvider] | None = None,
    ) -> Result[Sequence[BillingSource], ExternalAPIError]:
        async with self.session_manager.get_session() as session:
            billing_sources = await self.billing_source_repo.getByOrgId(
                session, org_id, providers
            )
            return Ok(billing_sources)

    async def updateBillingSource(
        self,
        org_id: str,
        billing_source_uid: uuid.UUID,
        update_fields: UpdateBillingSourceRequest,
    ) -> Result[
        None,
        InvalidEnumValueError
        | NotImplementedError
        | ExternalAPIError
        | BillingSourceNotFoundError,
    ]:
        async with self.session_manager.get_session() as session:
            billing_source = await self.billing_source_repo.getByUUID(
                session, billing_source_uid, org_id
            )
            if not billing_source:
                return Err(
                    BillingSourceNotFoundError(
                        message=f"Billing source with provider_id {billing_source_uid} not found for organization {org_id}"
                    )
                )
            session.expunge_all()

        if billing_source.source_type == BillingSourceProvider.STRIPE:
            await asyncio.to_thread(
                self._updateStripeCustomer,
                billing_source.provider_id,
                update_fields,
            )
        elif billing_source.source_type == BillingSourceProvider.PAYPAL:
            return Err(NotImplementedError())
        else:
            return Err(InvalidEnumValueError())

        return Ok(None)

    async def deleteBillingSource(
        self,
        org_id: str,
        billing_source_uid: uuid.UUID,
    ) -> Result[
        None,
        ExternalAPIError
        | BillingSourceNotFoundError
        | NotImplementedError
        | InvalidEnumValueError,
    ]:
        async with self.session_manager.get_session() as session:
            billing_source = (
                await self.billing_source_repo.markBillingSourceDeletedBuUUID(
                    session, billing_source_uid, org_id
                )
            )
            if not billing_source:
                return Err(
                    BillingSourceNotFoundError(
                        message=f"Billing source with provider_id {billing_source_uid} not found for organization {org_id}"
                    )
                )
            session.expunge_all()
            await session.commit()

        if billing_source.source_type == BillingSourceProvider.STRIPE:
            await asyncio.to_thread(
                self._deleteStripeCustomer, billing_source.provider_id
            )
        elif billing_source.source_type == BillingSourceProvider.PAYPAL:
            return Err(NotImplementedError())
        else:
            return Err(InvalidEnumValueError())

        async with self.session_manager.get_session() as session:
            await self.billing_source_repo.deleteBillingSourceById(
                session, billing_source.id
            )
            await session.commit()
        return Ok(None)

    def _deleteStripeCustomer(
        self, stripe_customer_id: str
    ) -> Result[None, ExternalAPIError]:
        try:
            self.stripe_client.v1.customers.delete(stripe_customer_id)
            return Ok(None)
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
                    message=f"Unexpected error: {str(e)}", from_exception=e
                )
            )

    def _updateStripeCustomer(
        self, stripe_customer_id: str, req: UpdateBillingSourceRequest
    ) -> Result[None, ExternalAPIError]:
        try:
            info_to_update: CustomerUpdateParams = {}
            if req.new_email:
                info_to_update["email"] = req.new_email
            if req.new_phone:
                info_to_update["phone"] = req.new_phone
            if req.new_address:
                info_to_update["address"] = {
                    "line1": req.new_address.line1,
                    "line2": req.new_address.line2,
                    "city": req.new_address.city,
                    "state": req.new_address.state,
                    "postal_code": req.new_address.postal_code,
                    "country": req.new_address.country,
                }
            self.stripe_client.v1.customers.update(
                stripe_customer_id, info_to_update
            )
            return Ok(None)
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
                    message=f"Unexpected error: {str(e)}", from_exception=e
                )
            )

    def _createStripeCustomer(
        self, req: AddBillingSourceRequest
    ) -> Result[str, ExternalAPIError]:
        try:
            customer = self.stripe_client.v1.customers.create(
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
            return Ok(customer.id)
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
                    message=f"Unexpected error: {str(e)}", from_exception=e
                )
            )
