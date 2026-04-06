from src.db.session import AsyncSessionManager
from src.shared.custom_types.error_exception import (
    ExternalAPIError,
    RecoverableError,
    NotImplementedError,
    InvalidEnumValueError,
)

from ..dtos import (
    BillingSourceResponse,
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from ..models import BillingSource, BillingSourceProvider
from .billing_source_stripe import (
    StripeBillingSourceProviderInterface,
)
from .billing_source_provider import (
    BillingSourceProviderInterface,
)
from ..repositories.billing_source_repo import BillingSourceRepo

import uuid

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

    async def createBillingSource(
        self, org_id: str, req: AddBillingSourceRequest
    ) -> Result[BillingSourceResponse, ExternalAPIError]:
        provider_imp = self.provider_impl[BillingSourceProvider.STRIPE]
        stripe_api_call_res = await provider_imp.createCustomer(req)
        if stripe_api_call_res.status == ResultStatus.Err:
            return stripe_api_call_res.into()

        stripe_customer_id = stripe_api_call_res.value
        async with self.session_manager.get_session() as session:
            billing_source = BillingSource(
                organization_id=org_id,
                source_type=BillingSourceProvider.STRIPE,
                provider_id=stripe_customer_id,
            )
            await self.billing_source_repo.add(session, billing_source)
            session.expunge_all()
            await session.commit()

        return Ok(
            BillingSourceResponse(
                billing_source_uid=billing_source.uuid,
                organization_id=billing_source.organization_id,
                source_type=billing_source.source_type,
                created_at=billing_source.created_at,
            )
        )

    async def updateBillingSource(
        self,
        org_id: str,
        update_fields: UpdateBillingSourceRequest,
    ) -> Result[
        None,
        InvalidEnumValueError
        | NotImplementedError
        | ExternalAPIError
        | BillingSourceNotFoundError,
    ]:
        billing_source_res = await self._getBillingSourceOrError(org_id)
        if billing_source_res.status == ResultStatus.Err:
            return billing_source_res.into()
        billing_source = billing_source_res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        await provider_imp.updateCustomer(
            billing_source.provider_id, update_fields
        )
        return Ok(None)

    async def getBillingSource(
        self,
        org_id: str,
    ):
        billing_source_res = await self._getBillingSourceOrError(org_id)
        if billing_source_res.status == ResultStatus.Err:
            return billing_source_res.into()
        billing_source = billing_source_res.value
        return Ok(
            BillingSourceResponse(
                billing_source_uid=billing_source.uuid,
                organization_id=billing_source.organization_id,
                source_type=billing_source.source_type,
                created_at=billing_source.created_at,
            )
        )

    async def _getBillingSourceOrError(
        self, org_id: str
    ) -> Result[BillingSource, BillingSourceNotFoundError]:
        async with self.session_manager.get_session() as session:
            billing_source = await self.billing_source_repo.getForOrg(
                session, org_id
            )
            if not billing_source:
                return Err(
                    BillingSourceNotFoundError(
                        message=f"Billing source not found for org {org_id}"
                    )
                )
            session.expunge_all()
            return Ok(billing_source)

    async def createSetupIntent(
        self, org_id: str
    ) -> Result[
        dict,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.createSetupIntent(billing_source.provider_id)

    async def listRequiredActionSetupIntents(
        self,
        org_id: str,
    ) -> Result[
        list,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
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
        setup_intent_id: str,
    ) -> Result[
        None,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.cancelSetupIntent(setup_intent_id)

    async def listPaymentMethods(
        self,
        org_id: str,
    ) -> Result[
        list,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
        if res.status == ResultStatus.Err:
            return res.into()

        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.listPaymentMethods(billing_source.provider_id)

    async def getPaymentMethodDetails(
        self,
        org_id: str,
        payment_method_id: str,
    ) -> Result[
        dict,
        ExternalAPIError
        | BillingSourceNotFoundError
        | InvalidEnumValueError
        | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
        if res.status == ResultStatus.Err:
            return res.into()
        billing_source = res.value
        return await self.provider_impl[
            billing_source.source_type
        ].getPaymentMethod(payment_method_id)

    async def deletePaymentMethod(
        self,
        org_id: str,
        payment_method_id: str,
    ) -> Result[
        None,
        ExternalAPIError | BillingSourceNotFoundError | NotImplementedError,
    ]:
        res = await self._getBillingSourceOrError(org_id)
        if res.status == ResultStatus.Err:
            return res.into()
        billing_source = res.value
        provider_imp = self.provider_impl[billing_source.source_type]
        return await provider_imp.detachPaymentMethod(payment_method_id)
