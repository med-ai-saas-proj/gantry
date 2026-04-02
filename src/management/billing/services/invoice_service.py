from src.db.session import AsyncSessionManager
from src.management.billing.dtos import (
    InvoiceInfoResponse,
    InvoiceItemInfoResponse,
    InvoiceDetailInfoResponse,
)
from src.shared.custom_types.error_exception import RecoverableError

from ..repositories.invoice_repo import InvoiceRepo

from uuid import UUID
from typing import Sequence
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
    ):
        self.session_manager = session_manager
        self.invoice_repo = invoice_repo

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
