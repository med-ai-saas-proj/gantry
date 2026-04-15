from gantry.db.session import AsyncSessionManager
from gantry.shared.utils.redis import redis_lock
from gantry.management.billing.dtos import (
    BillingSourceResponse,
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
)
from gantry.shared.custom_types.error_exception import (
    ExternalAPIError,
    RecoverableError,
    NotImplementedError,
    InvalidEnumValueError,
)

from ..dtos import (
    BillingSourceResponse,
    BillingAddressResponse,
    AddBillingSourceRequest,
    UpdateBillingSourceRequest,
    BillingSourceDetailResponse,
)
from ..models import BillingSource, BillingSourceProvider
from .billing_source_stripe import (
    StripeBillingSourceProviderInterface,
)
from .billing_source_provider import (
    BillingSourceProviderInterface,
)
from ..repositories.billing_source_repo import BillingSourceRepo

from typing import cast

from stripe import Customer, StripeClient
from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis


class BillingSourceNotFoundError(RecoverableError):
    status = 404
    code = "billing_source_not_found"
    title = "Billing Source Not Found"
    detail = "The billing source for the organization was not found."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class BillingSourceAlreadyExistsError(RecoverableError):
    status = 400
    code = "billing_source_already_exists"
    title = "Billing Source Already Exists"
    detail = "A billing source already exists for the organization."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class BillingSourceService:
    provider_impl: dict[BillingSourceProvider, BillingSourceProviderInterface]

    def __init__(
        self,
        billing_source_repo: BillingSourceRepo,
        session_manager: AsyncSessionManager,
        redis_client: Redis,
        stripe_client: StripeClient,
    ) -> None:
        self.billing_source_repo = billing_source_repo
        self.session_manager = session_manager
        self.redis_client = redis_client
        self.stripe_client = stripe_client
        self.provider_impl = {
            BillingSourceProvider.STRIPE: StripeBillingSourceProviderInterface(
                stripe_client=stripe_client
            )
        }

    async def createBillingSource(
        self, org_id: str, req: AddBillingSourceRequest
    ) -> Result[
        BillingSourceResponse,
        ExternalAPIError | BillingSourceAlreadyExistsError,
    ]:
        async with redis_lock(
            self.redis_client,
            f"billing_source_creation_lock:{org_id}",
        ) as lock_acquired:
            existed = await self._getBillingSourceOrError(org_id)
            if existed.status == ResultStatus.Ok:
                return Err(
                    BillingSourceAlreadyExistsError(
                        message=f"Billing source already exists for org {org_id}"
                    )
                )

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
    ) -> Result[
        BillingSourceDetailResponse,
        ExternalAPIError | BillingSourceNotFoundError | NotImplementedError,
    ]:
        billing_source_res = await self._getBillingSourceOrError(org_id)
        if billing_source_res.status == ResultStatus.Err:
            return billing_source_res.into()
        billing_source = billing_source_res.value
        source_type = billing_source.source_type
        billing_source_details_res = await self.provider_impl[
            source_type
        ].getCustomer(billing_source.provider_id)
        if billing_source_details_res.status == ResultStatus.Err:
            return billing_source_details_res.into()

        if source_type == BillingSourceProvider.STRIPE:
            billing_source_details = cast(
                Customer, billing_source_details_res.value
            )
            return Ok(
                BillingSourceDetailResponse(
                    billing_source_uid=billing_source.uuid,
                    organization_id=billing_source.organization_id,
                    source_type=billing_source.source_type,
                    created_at=billing_source.created_at,
                    provider_id=billing_source.provider_id,
                    email=billing_source_details.email,
                    phone=billing_source_details.phone,
                    name=billing_source_details.name,
                    billing_address=BillingAddressResponse(
                        line1=billing_source_details.address.line1,
                        line2=billing_source_details.address.line2,
                        city=billing_source_details.address.city,
                        state=billing_source_details.address.state,
                        postal_code=billing_source_details.address.postal_code,
                        country=billing_source_details.address.country,
                    )
                    if billing_source_details.address
                    else None,
                )
            )
        return Err(NotImplementedError())

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
