from src.db.repository import Repository
from src.management.billing.type import (
    BillingInvoiceInfo,
    BillingInvoiceLineItemInfo,
)

from ..models import BillingInvoice, BillingInvoiceLineItem

from uuid import UUID
from typing import Sequence
from datetime import datetime

from sqlalchemy import func, select


class InvoiceRepo(Repository[BillingInvoice, int]):
    """Repository for invoices."""

    def __init__(self):
        super().__init__(BillingInvoice, BillingInvoice.id)

    async def listInvoices(
        self,
        session,
        org_id: str,
        offset: int = 0,
        limit: int = 100,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        paid: bool | None = None,
    ) -> tuple[Sequence[BillingInvoiceInfo], int]:
        stmt = (
            select(BillingInvoice, func.count().over().label("total"))
            .select_from(BillingInvoice)
            .where(self.model.organization_id == org_id)
        )
        if from_date is not None:
            stmt = stmt.where(BillingInvoice.billing_period >= from_date)
        if to_date is not None:
            stmt = stmt.where(BillingInvoice.billing_period <= to_date)
        if paid is not None:
            if paid:
                stmt = stmt.where(BillingInvoice.paid_at.is_not(None))
            else:
                stmt = stmt.where(BillingInvoice.paid_at.is_(None))
        stmt = stmt.offset(offset).limit(limit)
        res = await session.execute(stmt)
        rows = res.all()
        return [
            {
                "invoice_id": row.BillingInvoice.id,
                "invoice_uid": row.uuid,
                "billing_period": row.billing_period,
                "total_amount": row.total_amount,
                "used_credits": row.used_credits,
                "provider_invoice_id": row.provider_invoice_id,
                "paid_at": row.paid_at,
                "details": row.details,
            }
            for row in rows[0]
        ], rows[0].total if rows else 0

    async def getInvoiceInfoByUUID(
        self,
        session,
        invoice_uid: UUID,
        org_id: str,
    ) -> BillingInvoiceInfo | None:
        stmt = select(BillingInvoice).where(
            BillingInvoice.uuid == invoice_uid,
            BillingInvoice.organization_id == org_id,
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        if not row:
            return None
        return {
            "invoice_id": row.id,
            "invoice_uid": row.uuid,
            "billing_period": row.billing_period,
            "total_amount": row.total_amount,
            "used_credits": row.used_credits,
            "provider_invoice_id": row.provider_invoice_id,
            "paid_at": row.paid_at,
            "details": row.details,
        }

    async def getInvoiceLineItems(
        self,
        session,
        invoice_id: int,
    ) -> Sequence[BillingInvoiceLineItemInfo]:
        # For simplicity, assume line items are stored as a JSON array in the details column of the invoice
        stmt = select(BillingInvoiceLineItem).where(
            BillingInvoiceLineItem.invoice_id == invoice_id
        )
        res = await session.execute(stmt)
        rows = res.scalars().all()
        return [
            {
                "description": row.description,
                "amount": row.amount,
                "project_uid": row.project_uid,
            }
            for row in rows
        ]
