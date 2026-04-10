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
from src.shared.custom_types.error_exception import RecoverableError
from src.management.billing.repositories.transaction_repo import (
    TransactionRepository,
)

from ..repositories.invoice_repo import InvoiceRepo

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import datetime

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
    ):
        self.session_manager = session_manager
        self.invoice_repo = invoice_repo
        self.transaction_repo = transaction_repo

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
            invs, total = await self.invoice_repo.listInvoices(
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
            inv = await self.invoice_repo.getInvoiceInfoByUUID(
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
                        )
                        for line in lines
                    ],
                )
            )

    async def createInvoice(
        self,
        org_id: str,
        now: datetime,
    ):
        current_period = _get_billing_period(now)
        previous_period = _get_previous_billing_period(current_period)
        previous_previous_period = _get_previous_billing_period(previous_period)

        async with self.session_manager.get_session() as session:
            have_invoice = await self.invoice_repo.haveInvoiceForBillingPeriod(
                session=session,
                org_id=org_id,
                billing_period=current_period.date(),
            )
            if have_invoice:
                return

            have_pending = await self.transaction_repo.havePendingTransactionsForOrgInPeriod(
                session=session,
                org_id=org_id,
                start_time=previous_period,
                end_time=current_period,
            )
            if have_pending:
                return

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
                        "description": f"Usage from {usage['period_bucket'].date()}",
                        "amount": usage["total_amount"],
                        "project_id": usage["group_by_int_key"],
                    }
                )
            total_amount = sum(line["amount"] for line in lines)
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
            await session.commit()
