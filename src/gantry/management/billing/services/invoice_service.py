from gantry.db.session import AsyncSessionManager
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
    InternalServiceError,
)

from ..dtos import (
    InvoiceInfoResponse,
    InvoiceItemInfoResponse,
    InvoiceDetailInfoResponse,
)
from ..type import (
    AggregatePeriod,
    CreateBillingInvoiceLineItemInfo,
)
from ..utils import (
    get_billing_period,
    get_previous_billing_period,
)
from ..models import BillingSourceProvider
from ..repositories.credit_repo import CreditRepo
from ..repositories.invoice_repo import InvoiceRepo
from ..repositories.transaction_repo import (
    TransactionRepository,
)
from ..services.billing_source_service import (
    BillingSourceAlreadyExistsError,
)
from ..repositories.billing_source_repo import (
    BillingSourceRepo,
)

import uuid
import asyncio
from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import UTC, datetime

from stripe import Invoice, StripeError, StripeClient
from pyrusult import Ok, Err, Result, ResultStatus
from structlog.stdlib import BoundLogger


class InvoiceNotFoundError(RecoverableError):
    status = 404
    code = "invoice_not_found"
    title = "Invoice Not Found"
    detail = "The requested invoice was not found."


class InvoiceAlreadyExistsError(RecoverableError):
    status = 400
    code = "invoice_already_exists"
    title = "Invoice Already Exists"
    detail = "An invoice for the current billing period already exists."


class ExistingPendingTransactionsError(RecoverableError):
    status = 400
    code = "existing_pending_transactions"
    title = "Existing Pending Transactions"
    detail = "There are existing pending transactions for the organization in the current billing period. Try again later."


class InvoiceAlreadyHasProviderInvoiceIDError(RecoverableError):
    status = 400
    code = "invoice_already_has_provider_invoice_id"
    title = "Invoice Already Has Provider Invoice ID"
    detail = "The invoice already has a provider invoice ID, cannot create another one in the billing provider."


class InvoiceService:
    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        invoice_repo: InvoiceRepo,
        transaction_repo: TransactionRepository,
        billing_source_repo: BillingSourceRepo,
        stripe_client: StripeClient,
        credit_repo: CreditRepo,
    ):
        self.logger = logger
        self.session_manager = session_manager
        self.invoice_repo = invoice_repo
        self.transaction_repo = transaction_repo
        self.billing_source_repo = billing_source_repo
        self.stripe_client = stripe_client
        self.credit_repo = credit_repo

    async def markInvoiceAsPaidManually(
        self,
        org_id: str,
        invoice_uid: UUID,
    ) -> Result[None, InvoiceNotFoundError]:
        async with self.session_manager.get_session() as session:
            res = await self.invoice_repo.markInvoiceAsPaidManually(
                session=session,
                org_id=org_id,
                invoice_uid=invoice_uid,
                paid_at=datetime.now(UTC).replace(tzinfo=None),
            )
            if not res:
                return Err(InvoiceNotFoundError())
            await session.commit()
            return Ok(None)

    async def markInvoiceAsRefundedManually(
        self,
        org_id: str,
        invoice_uid: UUID,
    ) -> Result[None, InvoiceNotFoundError]:
        async with self.session_manager.get_session() as session:
            res = await self.invoice_repo.markInvoiceAsRefundedManually(
                session=session,
                org_id=org_id,
                invoice_uid=invoice_uid,
                refunded_at=datetime.now(UTC).replace(tzinfo=None),
            )
            if not res:
                return Err(InvoiceNotFoundError())
            await session.commit()
            return Ok(None)

    async def markInvoiceAsPaid(
        self,
        provider: BillingSourceProvider,
        provider_id: str,
        paid_at: datetime,
    ) -> Result[None, InvoiceNotFoundError]:
        async with self.session_manager.get_session() as session:
            inv = await self.invoice_repo.markInvoiceAsPaid(
                session, provider, provider_id, paid_at
            )
            if inv is None:
                return Err(InvoiceNotFoundError())
            await session.commit()
            return Ok(None)

    async def listInvoices(
        self,
        org_id: str,
        offset: int = 0,
        limit: int = 100,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        paid: bool | None = None,
    ) -> Result[tuple[Sequence[InvoiceInfoResponse], int], None]:
        async with self.session_manager.get_session() as session:
            invs, total = await self.invoice_repo.listReadyInvoices(
                session=session,
                org_id=org_id,
                offset=offset,
                limit=limit,
                from_date=from_date,
                to_date=to_date,
                paid=paid,
            )
            return Ok(
                (
                    [
                        InvoiceInfoResponse(
                            invoice_uid=inv["invoice_uid"],
                            billing_period=inv["billing_period"],
                            total_amount=inv["total_amount"],
                            paid_at=inv["paid_at"],
                            details=inv["details"],
                            used_credits=inv["used_credits"],
                        )
                        for inv in invs
                    ],
                    total,
                )
            )

    async def getInvoiceById(
        self,
        org_id: str,
        invoice_uid: UUID,
    ) -> Result[InvoiceDetailInfoResponse, InvoiceNotFoundError]:
        async with self.session_manager.get_session() as session:
            inv = await self.invoice_repo.getReadyInvoiceInfoByUUID(
                session=session,
                org_id=org_id,
                invoice_uid=invoice_uid,
            )
            if not inv:
                return Err(InvoiceNotFoundError())

            lines = await self.invoice_repo.getInvoiceLineItems(
                session=session,
                invoice_id=inv["invoice_id"],
            )
            return Ok(
                InvoiceDetailInfoResponse(
                    invoice_uid=inv["invoice_uid"],
                    billing_period=inv["billing_period"],
                    total_amount=inv["total_amount"],
                    paid_at=inv["paid_at"],
                    details=inv["details"],
                    used_credits=inv["used_credits"],
                    line_items=[
                        InvoiceItemInfoResponse(
                            description=line["description"],
                            amount=line["amount"],
                            project_uuid=line["project_uuid"],
                            project_name=line["project_name"],
                        )
                        for line in lines
                    ],
                )
            )

    async def getInvoiceByIdPaymentLinkInProvider(
        self,
        org_id: str,
        invoice_uid: UUID,
    ) -> Result[
        str, InvoiceNotFoundError | NotImplementedError | InternalServiceError
    ]:
        async with self.session_manager.get_session() as session:
            inv = await self.invoice_repo.getReadyInvoiceInfoByUUID(
                session=session,
                org_id=org_id,
                invoice_uid=invoice_uid,
            )
            if not inv:
                return Err(InvoiceNotFoundError())

            if not inv["provider_invoice_id"] or not inv["provider"]:
                return Err(InvoiceNotFoundError())

            if inv["provider"] == BillingSourceProvider.STRIPE:
                invoice_res = await self.getInvoiceInStripe(
                    inv["provider_invoice_id"]
                )
                if invoice_res.status == ResultStatus.Err:
                    return invoice_res.into()
                invoice = invoice_res.unwrap()
                if invoice.hosted_invoice_url:
                    return Ok(invoice.hosted_invoice_url)
                return Err(
                    InternalServiceError(
                        message="Invoice does not have a hosted invoice URL in Stripe"
                    )
                )
            else:
                self.logger.error(
                    "Unsupported billing provider for getting payment link",
                    provider=inv["provider"],
                    org_id=org_id,
                )
                return Err(NotImplementedError())

    async def getInvoiceInStripe(
        self,
        invoice_provider_id: str,
    ) -> Result[Invoice, InternalServiceError]:
        try:
            invoice = await self.stripe_client.v1.invoices.retrieve_async(
                invoice_provider_id
            )
            return Ok(invoice)
        except StripeError as e:
            return Err(
                InternalServiceError(
                    message="Error retrieving invoice from Stripe",
                    from_exception=e,
                )
            )

    async def processInvoicesTask(
        self,
        sleep_interval_seconds: int,
    ):
        """Background task to process invoice creation and syncing with Stripe."""
        while True:
            now = datetime.now(UTC).replace(tzinfo=None)
            task_id: uuid.UUID = uuid.uuid4()
            try:
                self.logger.info(
                    f"Starting invoice processing task at {now.isoformat()}, Task ID: {task_id}",
                    task_id=task_id,
                )
                await self.processingInvoices(task_id, now)
                self.logger.info(
                    f"Completed invoice processing task at {datetime.now(UTC).isoformat()}, Task ID: {task_id}",
                    task_id=task_id,
                )
            except Exception as e:
                self.logger.error(
                    f"Error in processing invoices task, Task ID: {task_id}",
                    error=e,
                    task_id=task_id,
                )
            await asyncio.sleep(sleep_interval_seconds)

    async def processingInvoices(self, task_id: uuid.UUID, now: datetime):
        current_period = get_billing_period(now)
        previous_period = get_previous_billing_period(current_period)

        async with self.session_manager.get_session() as session:
            org_ids = await self.invoice_repo.getOrgsWithInvoiceToCreate(
                session,
                current_period,
                previous_period,
            )

        for org_id in org_ids:
            try:
                self.logger.info(
                    f"Creating invoice for org {org_id}, Task ID: {task_id}, period: {current_period.date()}",
                    org_id=org_id,
                    task_id=task_id,
                    billing_period=current_period.date(),
                )
                res = await self.createInvoice(
                    org_id,
                    current_period,
                    previous_period,
                )
                res.unwrap()
                self.logger.info(
                    f"Successfully created invoice for org {org_id}, Task ID: {task_id}, period: {current_period.date()}",
                    org_id=org_id,
                    task_id=task_id,
                    billing_period=current_period.date(),
                )
            except RecoverableError as e:
                print(e)
                self.logger.warning(
                    f"Recoverable error creating invoice for org {org_id}, Task ID: {task_id}, error: {e.detail}",
                    org_id=org_id,
                    task_id=task_id,
                    error=e,
                )
            except Exception as e:
                print(e)
                self.logger.error(
                    f"Error creating invoice for org {org_id}, Task ID: {task_id}",
                    error=e,
                    task_id=task_id,
                )

        async with self.session_manager.get_session() as session:
            row = await self.invoice_repo.getInvoicesToProcessInProvider(
                session
            )

        for invoice_id, org_id, provider in row:
            try:
                self.logger.info(
                    f"Processing invoice {invoice_id} for org {org_id} in provider {provider}, Task ID: {task_id}",
                    invoice_id=invoice_id,
                    org_id=org_id,
                    provider=provider,
                    task_id=task_id,
                )
                if provider == BillingSourceProvider.STRIPE:
                    res = await self.createInvoiceInStripe(org_id, invoice_id)
                    res.unwrap()
                else:
                    self.logger.error(
                        "Unsupported billing provider",
                        provider=provider,
                        org_id=org_id,
                    )
                self.logger.info(
                    f"Successfully processed invoice {invoice_id} for org {org_id} in provider {provider}, Task ID: {task_id}",
                    invoice_id=invoice_id,
                    org_id=org_id,
                    provider=provider,
                    task_id=task_id,
                )
            except StripeError as e:
                print(e)
                self.logger.error(
                    "Stripe error processing invoice for org",
                    org_id=org_id,
                    error=e,
                )
            except RecoverableError as e:
                self.logger.warning(
                    f"Recoverable error processing invoice for org {org_id}, Task ID: {task_id}, error: {e.detail}",
                    org_id=org_id,
                    task_id=task_id,
                    error=e,
                )
            except Exception as e:
                self.logger.error(
                    "Error processing invoice for org", org_id=org_id, error=e
                )

    async def createInvoice(
        self,
        org_id: str,
        current_period: datetime,
        previous_period: datetime,
    ) -> Result[
        UUID, InvoiceAlreadyExistsError | ExistingPendingTransactionsError
    ]:
        async with self.session_manager.get_session() as session:
            have_invoice = await self.invoice_repo.haveInvoiceForBillingPeriod(
                session=session,
                org_id=org_id,
                billing_period=current_period.date(),
            )
            if have_invoice:
                return Err(InvoiceAlreadyExistsError())

            have_pending = await self.transaction_repo.havePendingTransactionsForOrgInPeriod(
                session=session,
                org_id=org_id,
                start_time=previous_period,
                end_time=current_period,
            )
            if have_pending:
                return Err(ExistingPendingTransactionsError())

            total_usage = await self.transaction_repo.sumByPeriodByProjectsGroupedByProjects(
                session=session,
                org_id=org_id,
                project_ids=None,  # all projects
                start_time=previous_period,
                end_time=current_period,
                period=AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            lines: list[CreateBillingInvoiceLineItemInfo] = []
            for usage in total_usage:
                print(usage)
                lines.append(
                    {
                        "description": f"Usage in {usage['period_bucket'].date()}: {usage['group_by_name']}",
                        "amount": usage["total_amount"],
                        "project_id": usage["group_by_int_key"],
                    }
                )
            total_amount = sum([line["amount"] for line in lines], Decimal(0))
            details = {
                "period_start": previous_period.isoformat(),
                "period_end": current_period.isoformat(),
            }

            if total_amount == 0:
                res = await self.invoice_repo.createInvoice(
                    session=session,
                    org_id=org_id,
                    billing_period=current_period.date(),
                    total_amount=total_amount,
                    details=details,
                    used_credits=Decimal(0),
                )
                if len(lines) > 0:
                    await self.invoice_repo.createInvoiceLineItems(
                        session=session,
                        invoice_id=res["invoice_id"],
                        lines=lines,
                    )
                await session.commit()
                return Ok(res["invoice_uid"])

            credit = await self.credit_repo.getCreditForOrgWithLock(
                session=session,
                org_id=org_id,
                read=False,
            )
            credits_available = credit.amount if credit else Decimal(0)
            used_credits = Decimal(0)
            if credits_available > 0:
                if credits_available >= total_amount:
                    used_credits = total_amount
                    leftover_credits = credits_available - total_amount
                else:
                    used_credits = credits_available
                    leftover_credits = Decimal(0)
                await self.credit_repo.setCreditForOrg(
                    session=session,
                    org_id=org_id,
                    new_amount=leftover_credits,
                )
                await self.credit_repo.createCreditTransaction(
                    session=session,
                    org_id=org_id,
                    amount=-used_credits,
                    description=f"Applied credits to invoice for period {current_period.date()}",
                )

            res = await self.invoice_repo.createInvoice(
                session=session,
                org_id=org_id,
                billing_period=current_period.date(),
                total_amount=total_amount,
                details=details,
                used_credits=used_credits,
            )
            if len(lines) > 0:
                await self.invoice_repo.createInvoiceLineItems(
                    session=session,
                    invoice_id=res["invoice_id"],
                    lines=lines,
                )
            await session.commit()
            return Ok(res["invoice_uid"])

    async def createInvoiceInStripe(
        self,
        org_id: str,
        invoice_id: int,
    ) -> Result[
        str,
        BillingSourceAlreadyExistsError
        | InvoiceNotFoundError
        | InvoiceAlreadyHasProviderInvoiceIDError,
    ]:
        async with self.session_manager.get_session() as session:
            billing_source = await self.billing_source_repo.getWithLock(
                session=session,
                org_id=org_id,
                provider=BillingSourceProvider.STRIPE,
                read=True,
            )
            if not billing_source:
                self.logger.error(
                    "No billing source found for org", org_id=org_id
                )
                return Err(InvoiceNotFoundError())

            inv = await self.invoice_repo.getInvoiceInfoByIdWithLock(
                session=session,
                invoice_id=invoice_id,
                read=False,
            )
            if not inv:
                return Err(InvoiceNotFoundError())
            if inv["provider_invoice_id"]:
                # Invoice already created in Stripe
                return Err(InvoiceAlreadyHasProviderInvoiceIDError())

            line_items = await self.invoice_repo.getInvoiceLineItems(
                session=session,
                invoice_id=inv["invoice_id"],
            )
            customer_id = billing_source.provider_id
            invoice_uid = inv["invoice_uid"]

            invoice = await self.stripe_client.v1.invoices.create_async(
                {
                    "customer": customer_id,
                    "auto_advance": False,  # we will finalize it later after adding line items
                    "collection_method": "charge_automatically",
                    "description": f"Invoice for {inv['billing_period']}",
                    "metadata": {
                        "invoice_uid": str(invoice_uid),
                        "org_id": org_id,
                    },
                },
                {
                    "idempotency_key": f"inv_{org_id}_{invoice_uid}",
                },
            )

            for line in line_items:
                await self.stripe_client.v1.invoice_items.create_async(
                    {
                        "amount": int(
                            line["amount"] * 100
                        ),  # Stripe expects amount in cents
                        "currency": "usd",
                        "invoice": invoice.id,
                        "customer": customer_id,
                        "description": line["description"],
                        "metadata": {
                            "invoice_uid": str(invoice_uid),
                            "invoice_line_uuid": str(line["invoice_line_uuid"]),
                            "org_id": org_id,
                            "project_uuid": str(line["project_uuid"])
                            if line["project_uuid"]
                            else "",
                        },
                    },
                    {
                        "idempotency_key": f"invoice_item_{org_id}_{invoice_uid}_{line['invoice_line_uuid']}",
                    },
                )

            if inv["used_credits"] > 0:
                await self.stripe_client.v1.invoice_items.create_async(
                    {
                        "amount": int(
                            -inv["used_credits"] * 100
                        ),  # negative amount for credit
                        "currency": "usd",
                        "invoice": invoice.id,
                        "customer": customer_id,
                        "description": f"Applied credits",
                        "metadata": {
                            "invoice_uid": str(invoice_uid),
                            "org_id": org_id,
                        },
                    },
                    {
                        "idempotency_key": f"invoice_item_{org_id}_{invoice_uid}_credits",
                    },
                )

            await self.stripe_client.v1.invoices.finalize_invoice_async(
                invoice.id,
                {"auto_advance": True},
                {
                    "idempotency_key": f"finalize_{org_id}_{invoice_uid}",
                },
            )

            await self.invoice_repo.updateProviderInvoiceID(
                session=session,
                provider=BillingSourceProvider.STRIPE,
                invoice_id=inv["invoice_id"],
                provider_invoice_id=invoice.id,
            )
            await session.commit()
            return Ok(invoice.id)
