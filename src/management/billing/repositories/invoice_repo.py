from src.db.repository import Repository
from src.management.billing.type import (
    BillingInvoiceInfo,
    BillingInvoiceLineItemInfo,
    CreateBillingInvoiceLineItemInfo,
)
from src.management.project.models import Project

from ..models import (
    BillingSource,
    BillingInvoice,
    TransactionStatus,
    BillingTransaction,
    BillingSourceProvider,
    BillingInvoiceLineItem,
)

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class InvoiceRepo(Repository[BillingInvoice, int]):
    """Repository for invoices."""

    def __init__(self):
        super().__init__(BillingInvoice, BillingInvoice.id)

    async def getInvoicesToProcessInProvider(
        self, session: AsyncSession
    ) -> Sequence[tuple[int, str, BillingSourceProvider]]:
        stmt = (
            select(
                BillingInvoice.id,
                BillingInvoice.organization_id,
                BillingSource.source_type.label("provider"),
            )
            .select_from(BillingInvoice)
            .join(
                BillingSource,
                BillingInvoice.organization_id == BillingSource.organization_id,
            )
            .where(BillingInvoice.provider_invoice_id.is_not(None))
        )
        res = await session.execute(stmt)
        return [
            (
                row.id,
                row.organization_id,
                row.provider,
            )
            for row in res.all()
        ]

    async def getOrgsWithInvoiceToCreate(
        self,
        session: AsyncSession,
        billing_period: date,
        prev_billing_period: date,
        prev_prev_billing_period: date,
    ) -> Sequence[str]:
        pending_tx_subq = (
            select(BillingTransaction.id).where(
                BillingTransaction.created_at >= prev_prev_billing_period,
                BillingTransaction.created_at < prev_billing_period,
                BillingTransaction.organization_id
                == BillingSource.organization_id,
                BillingTransaction.status == TransactionStatus.PENDING,
            )
        ).exists()
        stmt = (
            select(BillingSource.organization_id, BillingSource.source_type)
            .select_from(BillingSource)
            .where(
                BillingSource.organization_id.not_in(
                    select(BillingInvoice.organization_id).where(
                        BillingInvoice.billing_period == billing_period
                    )
                ),
                ~pending_tx_subq,
            )
        )
        res = await session.execute(stmt)
        return [row.organization_id for row in res.all()]

    async def listReadyInvoices(
        self,
        session: AsyncSession,
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
            .where(
                BillingInvoice.provider_invoice_id.is_not(None)
            )  # only return invoices that have been created in provider
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

    async def getReadyInvoiceInfoByUUID(
        self,
        session: AsyncSession,
        invoice_uid: UUID,
        org_id: str,
    ) -> BillingInvoiceInfo | None:
        stmt = select(BillingInvoice).where(
            BillingInvoice.uuid == invoice_uid,
            BillingInvoice.organization_id == org_id,
            BillingInvoice.provider_invoice_id.is_not(
                None
            ),  # only return if invoice has been created in provider
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

    async def getInvoiceInfoByIdWithLock(
        self,
        session: AsyncSession,
        invoice_id: int,
        read: bool = True,
    ) -> BillingInvoiceInfo | None:
        stmt = select(BillingInvoice).where(
            BillingInvoice.id == invoice_id,
        )
        if read:
            stmt = stmt.with_for_update(read=True)
        else:
            stmt = stmt.with_for_update(read=False)
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

    async def updateProviderInvoiceID(
        self,
        session: AsyncSession,
        invoice_id: int,
        provider_invoice_id: str,
    ):
        stmt = (
            update(BillingInvoice)
            .where(BillingInvoice.id == invoice_id)
            .values(provider_invoice_id=provider_invoice_id)
        )
        await session.execute(stmt)

    async def getInvoiceLineItems(
        self,
        session: AsyncSession,
        invoice_id: int,
    ) -> Sequence[BillingInvoiceLineItemInfo]:
        # For simplicity, assume line items are stored as a JSON array in the details column of the invoice
        stmt = (
            select(
                BillingInvoiceLineItem.uuid,
                BillingInvoiceLineItem.description,
                BillingInvoiceLineItem.amount,
                Project.uuid.label("project_uid"),
                Project.id.label("project_id"),
                Project.name.label("name"),
            )
            .select_from(BillingInvoiceLineItem)
            .join(
                Project,
                BillingInvoiceLineItem.project_id == Project.id,
                isouter=True,
            )
            .where(BillingInvoiceLineItem.invoice_id == invoice_id)
        )
        res = await session.execute(stmt)
        rows = res.all()
        return [
            {
                "invoice_line_uuid": row.uuid,
                "description": row.description,
                "amount": row.amount,
                "project_uid": row.project_uid,
                "project_id": row.project_id,
                "project_name": row.name,
            }
            for row in rows
        ]

    async def haveInvoiceForBillingPeriod(
        self,
        session: AsyncSession,
        org_id: str,
        billing_period: date,
    ) -> bool:
        stmt = select(BillingInvoice).where(
            BillingInvoice.organization_id == org_id,
            BillingInvoice.billing_period == billing_period,
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        return row is not None

    async def createInvoice(
        self,
        session: AsyncSession,
        org_id: str,
        billing_period: date,
        total_amount: Decimal,
        details: dict,
        used_credits: Decimal,
    ) -> BillingInvoiceInfo:
        new_inv = BillingInvoice(
            organization_id=org_id,
            billing_period=billing_period,
            total_amount=total_amount,
            provider_invoice_id=None,
            details=details,
            used_credits=used_credits,
            paid_at=None,
        )
        session.add(new_inv)
        await session.flush()  # to get the ID of the new invoice
        return {
            "invoice_id": new_inv.id,
            "invoice_uid": new_inv.uuid,
            "billing_period": new_inv.billing_period,
            "total_amount": new_inv.total_amount,
            "used_credits": new_inv.used_credits,
            "provider_invoice_id": None,
            "paid_at": new_inv.paid_at,
            "details": new_inv.details,
        }

    async def createInvoiceLineItems(
        self,
        session: AsyncSession,
        invoice_id: int,
        lines: list[CreateBillingInvoiceLineItemInfo],
    ):
        for line in lines:
            new_line = BillingInvoiceLineItem(
                invoice_id=invoice_id,
                description=line["description"],
                amount=line["amount"],
                project_id=line["project_id"],
            )
            session.add(new_line)
        await session.flush()
