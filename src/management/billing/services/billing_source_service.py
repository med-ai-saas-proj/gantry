from src.db.session import AsyncSessionManager
from src.management.billing.dtos import (
    BillingSourceResponse,
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from src.shared.custom_types.error_exception import (
    ExternalAPIError,
    RecoverableError,
    NotImplementedError,
    InvalidEnumValueError,
)
from src.management.billing.services.billing_source_stripe import (
    StripeBillingSourceProviderInterface,
)
from src.management.billing.services.billing_source_provider import (
    BillingSourceProviderInterface,
)

from ..models import BillingSource, BillingSourceState, BillingSourceProvider
from ..repositories.billing_source_repo import BillingSourceRepo

import re
import uuid
from typing import Sequence

from stripe import StripeClient
from pyrusult import Ok, Err, Result, ResultStatus


class BillingSourceNotFoundError(RecoverableError):
    status = 404
    code = "billing_source_not_found"
    title = "Billing Source Not Found"
    detail = "The specified billing source was not found for the organization."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class BillingSourceService:
    provider_impl: dict[BillingSourceProvider, BillingSourceProviderInterface]

    def __init__(
        self,
        billing_source_repo: BillingSourceRepo,
        session_manager: AsyncSessionManager,
        stripe_client: StripeClient,
    ) -> None:
        self.billing_source_repo = billing_source_repo
        self.session_manager = session_manager
        self.stripe_client = stripe_client
        self.provider_impl = {
            BillingSourceProvider.STRIPE: StripeBillingSourceProviderInterface(
                stripe_client=stripe_client
            )
        }

    async def addBillingSource(
        self, org_id: str, req: AddBillingSourceRequest
    ) -> Result[BillingSourceResponse, ExternalAPIError]:
        async with self.session_manager.get_session() as session:
            billing_source = BillingSource(
                organization_id=org_id,
                source_type=BillingSourceProvider.STRIPE,
                status=BillingSourceState.PENDING,
                provider_id="",  # Will be updated later when we get the Stripe customer ID
            )
            await self.billing_source_repo.add(session, billing_source)
            await session.commit()

        provider_imp = self.provider_impl[BillingSourceProvider.STRIPE]
        stripe_api_call_res = await provider_imp.createCustomer(req)
        if stripe_api_call_res.status == ResultStatus.Err:
            # If creating the customer in Stripe fails, we should clean up the pending billing source we created
            async with self.session_manager.get_session() as session:
                await self.billing_source_repo.deleteBillingSourceById(
                    session, billing_source.id
                )
                await session.commit()
            return stripe_api_call_res.into()

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

        return Ok(
            BillingSourceResponse(
                billing_source_uid=updated_billing_source.uuid,
                organization_id=updated_billing_source.organization_id,
                source_type=updated_billing_source.source_type,
                status=updated_billing_source.status,
                created_at=updated_billing_source.created_at,
            )
        )

    async def listBillingSources(
        self,
        org_id: str,
        providers: list[BillingSourceProvider] | None = None,
    ) -> Result[Sequence[BillingSourceResponse], ExternalAPIError]:
        async with self.session_manager.get_session() as session:
            billing_sources = await self.billing_source_repo.getByOrgId(
                session, org_id, providers
            )
            return Ok(
                [
                    BillingSourceResponse(
                        billing_source_uid=bs.uuid,
                        organization_id=bs.organization_id,
                        source_type=bs.source_type,
                        status=bs.status,
                        created_at=bs.created_at,
                    )
                    for bs in billing_sources
                ]
            )

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
        billing_source_res = await self._getBillingSourceOrError(
            org_id, billing_source_uid
        )
        if billing_source_res.status == ResultStatus.Err:
            return billing_source_res.into()
        billing_source = billing_source_res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        await provider_imp.updateCustomer(
            billing_source.provider_id, update_fields
        )
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

        provider_imp = self.provider_impl[billing_source.source_type]
        await provider_imp.deleteCustomer(billing_source.provider_id)

        async with self.session_manager.get_session() as session:
            await self.billing_source_repo.deleteBillingSourceById(
                session, billing_source.id
            )
            await session.commit()
        return Ok(None)

    async def _getBillingSourceOrError(
        self, org_id: str, billing_source_uid: uuid.UUID
    ) -> Result[BillingSource, BillingSourceNotFoundError]:
        async with self.session_manager.get_session() as session:
            billing_source = await self.billing_source_repo.getByUUID(
                session, billing_source_uid, org_id
            )
            if not billing_source:
                return Err(
                    BillingSourceNotFoundError(
                        message=f"Billing source {billing_source_uid} not found for org {org_id}"
                    )
                )
            session.expunge_all()
            return Ok(billing_source)

    async def createSetupIntent(
        self, org_id: str, billing_source_uid: uuid.UUID
    ) -> Result[
        dict,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.createSetupIntent(billing_source.provider_id)

    async def listRequiredActionSetupIntents(
        self, org_id: str, billing_source_uid: uuid.UUID
    ) -> Result[
        list,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.listRequiredActionSetupIntents(
            billing_source.provider_id
        )

    async def cancelSetupIntent(
        self,
        org_id: str,
        billing_source_uid: uuid.UUID,
        setup_intent_id: str,
    ) -> Result[
        None,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.cancelSetupIntent(setup_intent_id)

    async def listPaymentMethods(
        self, org_id: str, billing_source_uid: uuid.UUID
    ) -> Result[
        list,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.listPaymentMethods(billing_source.provider_id)

    async def getPaymentMethodDetails(
        self,
        org_id: str,
        billing_source_uid: uuid.UUID,
        payment_method_id: str,
    ) -> Result[
        dict,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()
        billing_source = res.value
        return await self.provider_impl[
            billing_source.source_type
        ].getPaymentMethod(payment_method_id)

    async def deletePaymentMethod(
        self,
        org_id: str,
        billing_source_uid: uuid.UUID,
        payment_method_id: str,
    ) -> Result[
        None,
        ExternalAPIError | BillingSourceNotFoundError | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id, billing_source_uid)
        if res.status == ResultStatus.Err:
            return res.into()
        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.detachPaymentMethod(payment_method_id)
