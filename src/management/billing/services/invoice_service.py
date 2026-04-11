from src.db.session import AsyncSessionManager
from src.management.billing.dtos import (
    InvoiceInfoResponse,
    InvoiceItemInfoResponse,
    InvoiceDetailInfoResponse,
)
from src.management.billing.type import (
    AggregatePeriod,
    BillingInvoiceLineItemInfo,
    CreateBillingInvoiceLineItemInfo,
)
from src.management.billing.utils import (
    _get_billing_period,
    _get_previous_billing_period,
)
from src.management.billing.models import BillingSourceProvider
from src.shared.custom_types.error_exception import (
    RecoverableError,
)
from src.management.billing.repositories.transaction_repo import (
    TransactionRepository,
)
from src.management.billing.repositories.billing_source_repo import (
    BillingSourceRepo,
)

from ..repositories.invoice_repo import InvoiceRepo

import asyncio
from uuid import UUID
from ctypes import cast
from typing import Sequence
from decimal import Decimal
from datetime import UTC, datetime

from stripe import StripeError, StripeClient
from pyrusult import Ok, Err, Result


class InvoiceNotFoundError(RecoverableError):
    status = 404
    code = "invoice_not_found"
    title = "Invoice Not Found"
    detail = "The requested invoice was not found."


class InvoiceService:
    def __init__(
        self,
        session_manager: AsyncSessionManager,
        invoice_repo: InvoiceRepo,
        transaction_repo: TransactionRepository,
        billing_source_repo: BillingSourceRepo,
        stripe_client: StripeClient,
    ):
        self.session_manager = session_manager
        self.invoice_repo = invoice_repo
        self.transaction_repo = transaction_repo
        self.billing_source_repo = billing_source_repo
        self.stripe_client = stripe_client

    async def list_invoices(
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

    async def get_invoice_by_id(
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
                            project_uid=line["project_uid"],
                            project_name=line["project_name"],
                        )
                        for line in lines
                    ],
                )
            )

    async def processInvoicesTask(self):
        """Background task to process invoice creation and syncing with Stripe."""
        while True:
            now = datetime.now(UTC).replace(tzinfo=None)
            try:
                await self.processingInvoices(now)
            except Exception as e:
                print(f"Error in processing invoices task: {e}")
            await asyncio.sleep(60 * 30)  # Run every 30 minutes

    async def processingInvoices(self, now: datetime):
        current_period = _get_billing_period(now)
        previous_period = _get_previous_billing_period(current_period)
        previous_previous_period = _get_previous_billing_period(previous_period)

        async with self.session_manager.get_session() as session:
            org_ids = await self.invoice_repo.getOrgsWithInvoiceToCreate(
                session,
                current_period.date(),
                previous_period,
                previous_previous_period,
            )

        for org_id in org_ids:
            try:
                await self.createInvoice(
                    org_id,
                    now,
                    current_period,
                    previous_period,
                    previous_previous_period,
                )
            except Exception as e:
                print(f"Error creating invoice for org {org_id}: {e}")

        async with self.session_manager.get_session() as session:
            row = await self.invoice_repo.getInvoicesToProcessInProvider(
                session
            )
        for invoice_id, org_id, provider in row:
            try:
                if provider == BillingSourceProvider.STRIPE:
                    await self.createInvoiceInStripe(org_id, invoice_id)
                else:
                    print(
                        f"Unsupported billing provider {provider} for org {org_id}"
                    )
            except StripeError as e:
                print(f"Stripe error processing invoice for org {org_id}: {e}")
            except Exception as e:
                print(f"Error processing invoice for org {org_id}: {e}")

    async def createInvoice(
        self,
        org_id: str,
        now: datetime,
        current_period: datetime,
        previous_period: datetime,
        previous_previous_period: datetime,
    ) -> UUID | None:
        async with self.session_manager.get_session() as session:
            have_invoice = await self.invoice_repo.haveInvoiceForBillingPeriod(
                session=session,
                org_id=org_id,
                billing_period=current_period.date(),
            )
            if have_invoice:
                return None

            have_pending = await self.transaction_repo.havePendingTransactionsForOrgInPeriod(
                session=session,
                org_id=org_id,
                start_time=previous_period,
                end_time=current_period,
            )
            if have_pending:
                return None

            total_usage = await self.transaction_repo.sumByPeriodByProjectsGroupedByProjects(
                session=session,
                org_id=org_id,
                project_ids=None,  # all projects
                start_time=previous_previous_period,
                end_time=previous_period,
                period=AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            lines: list[CreateBillingInvoiceLineItemInfo] = []
            for usage in total_usage:
                lines.append(
                    {
                        "description": f"Usage in {usage['period_bucket'].date()}: {usage['group_by_name']}",
                        "amount": usage["total_amount"],
                        "project_id": usage["group_by_int_key"],
                    }
                )
            total_amount = sum([line["amount"] for line in lines], Decimal(0))
            details = {
                "generated_at": now.isoformat(),
                "period_start": previous_period.isoformat(),
                "period_end": current_period.isoformat(),
            }
            async with session.begin():
                used_credits = Decimal("0")  # Placeholder for any credit logic
                res = await self.invoice_repo.createInvoice(
                    session=session,
                    org_id=org_id,
                    billing_period=current_period.date(),
                    total_amount=total_amount,
                    details=details,
                    used_credits=used_credits,
                )
                await self.invoice_repo.createInvoiceLineItems(
                    session=session,
                    invoice_id=res["invoice_id"],
                    lines=lines,
                )
                res_invoice_uid = res["invoice_uid"]
                await session.commit()
                return res_invoice_uid

    async def createInvoiceInStripe(
        self,
        org_id: str,
        invoice_id: int,
    ):
        async with self.session_manager.get_session() as session:
            async with session.begin():
                billing_source = await self.billing_source_repo.getWithLock(
                    session=session,
                    org_id=org_id,
                    provider=BillingSourceProvider.STRIPE,
                    read=True,
                )
                if not billing_source:
                    print(
                        f"No billing source found for org {org_id}, cannot create Stripe invoice"
                    )
                    return
                inv = await self.invoice_repo.getInvoiceInfoByIdWithLock(
                    session=session,
                    invoice_id=invoice_id,
                    read=False,
                )
                if not inv:
                    return Err(InvoiceNotFoundError())
                if inv["provider_invoice_id"]:
                    # Invoice already created in Stripe
                    return Ok(None)
                line_items = await self.invoice_repo.getInvoiceLineItems(
                    session=session,
                    invoice_id=inv["invoice_id"],
                )
                customer_id = billing_source.provider_id
                invoice_uid = inv["invoice_uid"]

                invoice = await self.stripe_client.v1.invoices.create_async(
                    {
                        "customer": customer_id,
                        "auto_advance": True,
                        "collection_method": "charge_automatically",
                        "idempotency_key": f"inv_{org_id}_{invoice_uid}",
                        "description": f"Invoice for {inv['billing_period']}",
                        "metadata": {
                            "invoice_uid": str(invoice_uid),
                            "org_id": org_id,
                        },
                    }
                )
                for line in line_items:
                    await self.stripe_client.v1.invoice_items.create_async(
                        {
                            "amount": int(
                                line["amount"] * 100
                            ),  # Stripe expects amount in cents
                            "currency": "usd",
                            "invoice": invoice.id,
                            "description": line["description"],
                            "idempotency_key": f"invitem_{org_id}_{invoice_uid}_{line['invoice_line_uuid']}",
                            "metadata": {
                                "invoice_uid": str(invoice_uid),
                                "invoice_line_uuid": str(
                                    line["invoice_line_uuid"]
                                ),
                                "org_id": org_id,
                                "project_uid": str(line["project_uid"])
                                if line["project_uid"]
                                else "",
                            },
                        }
                    )
                await self.stripe_client.v1.invoices.finalize_invoice_async(
                    invoice.id,
                    {
                        "idempotency_key": f"finalize_{org_id}_{invoice_uid}",
                    },
                )
                await self.invoice_repo.updateProviderInvoiceID(
                    session=session,
                    invoice_id=inv["invoice_id"],
                    provider_invoice_id=invoice.id,
                )
                await session.commit()
                return Ok(invoice.id)
