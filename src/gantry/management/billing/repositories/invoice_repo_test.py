from ..models import BillingSourceProvider
from .invoice_repo import InvoiceRepo

import unittest
from types import SimpleNamespace
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock


class InvoiceRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_invoices_to_process_in_provider_maps_rows(self):
        result = MagicMock()
        result.all.return_value = [
            SimpleNamespace(
                id=1,
                organization_id="org1",
                provider=BillingSourceProvider.STRIPE,
            )
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = InvoiceRepo()

        rows = await repo.getInvoicesToProcessInProvider(session)

        assert rows == [(1, "org1", BillingSourceProvider.STRIPE)]
        session.execute.assert_awaited_once()

    async def test_have_invoice_for_billing_period_returns_boolean(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = SimpleNamespace(id=1)
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = InvoiceRepo()

        assert (
            await repo.haveInvoiceForBillingPeriod(
                session,
                org_id="org1",
                billing_period=date(2026, 1, 1),
            )
            is True
        )

    async def test_create_invoice_builds_model_and_flushes(self):
        session = MagicMock()
        session.flush = AsyncMock()
        repo = InvoiceRepo()

        invoice = await repo.createInvoice(
            session=session,
            org_id="org1",
            billing_period=date(2026, 1, 1),
            total_amount=Decimal("12.5"),
            details={"note": "test"},
            used_credits=Decimal("2.5"),
        )

        new_invoice = session.add.call_args.args[0]
        assert new_invoice.organization_id == "org1"
        assert new_invoice.billing_period == date(2026, 1, 1)
        assert new_invoice.total_amount == Decimal("12.5")
        assert new_invoice.used_credits == Decimal("2.5")
        assert new_invoice.details == {"note": "test"}
        assert invoice["invoice_id"] == new_invoice.id
        assert invoice["billing_period"] == date(2026, 1, 1)
        session.flush.assert_awaited_once()

    async def test_create_invoice_line_items_adds_all_rows(self):
        session = MagicMock()
        session.flush = AsyncMock()
        repo = InvoiceRepo()

        await repo.createInvoiceLineItems(
            session=session,
            invoice_id=10,
            lines=[
                {
                    "description": "line1",
                    "amount": Decimal("1.0"),
                    "project_id": 1,
                },
                {
                    "description": "line2",
                    "amount": Decimal("2.0"),
                    "project_id": None,
                },
            ],
        )

        assert session.add.call_count == 2
        first_line = session.add.call_args_list[0].args[0]
        second_line = session.add.call_args_list[1].args[0]
        assert first_line.description == "line1"
        assert first_line.amount == Decimal("1.0")
        assert first_line.project_id == 1
        assert second_line.description == "line2"
        assert second_line.amount == Decimal("2.0")
        assert second_line.project_id is None
        session.flush.assert_awaited_once()
