from .credit_repo import CreditRepo

import unittest
from types import SimpleNamespace
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


class CreditRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_credit_by_org_id_returns_scalar_without_db(self):
        credit = SimpleNamespace(organization_id="org1", amount=Decimal("42.5"))
        result = MagicMock()
        result.scalar_one_or_none.return_value = credit
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = CreditRepo()

        found = await repo.getCreditByOrgId(session, "org1")

        assert found is credit
        session.execute.assert_awaited_once()

    async def test_get_credit_transactions_maps_rows_without_db(self):
        result = MagicMock()
        result.all.return_value = [
            SimpleNamespace(
                amount=Decimal("12.5"),
                description="Added credits",
                created_at=datetime(2026, 1, 15),
                total_count=3,
            )
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = CreditRepo()

        transactions, total = await repo.getCreditTransactions(
            session=session,
            org_id="org1",
            offset=0,
            limit=100,
        )

        assert transactions == [
            {
                "amount": Decimal("12.5"),
                "description": "Added credits",
                "created_at": datetime(2026, 1, 15),
            }
        ]
        assert total == 3
        session.execute.assert_awaited_once()

    async def test_get_credit_transactions_returns_empty_list_when_no_rows(
        self,
    ):
        result = MagicMock()
        result.all.return_value = []
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = CreditRepo()

        transactions, total = await repo.getCreditTransactions(
            session=session,
            org_id="org1",
        )

        assert transactions == []
        assert total == 0
        session.execute.assert_awaited_once()

    async def test_add_credit_for_org_returns_inserted_credit_without_db(self):
        credit = SimpleNamespace(organization_id="org1", amount=Decimal("25"))
        result = MagicMock()
        result.scalar_one.return_value = credit
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = CreditRepo()

        added = await repo.addCreditForOrg(
            session=session,
            org_id="org1",
            amount=Decimal("25"),
        )

        assert added is credit
        session.execute.assert_awaited_once()

    async def test_set_credit_for_org_executes_update_without_db(self):
        session = MagicMock()
        session.execute = AsyncMock()
        repo = CreditRepo()

        await repo.setCreditForOrg(
            session=session,
            org_id="org1",
            new_amount=Decimal("99.5"),
        )

        session.execute.assert_awaited_once()

    async def test_create_credit_transaction_adds_model(self):
        session = MagicMock()
        repo = CreditRepo()

        await repo.createCreditTransaction(
            session=session,
            org_id="org1",
            amount=Decimal("7.5"),
            description="Added credits",
        )

        transaction = session.add.call_args.args[0]
        assert transaction.organization_id == "org1"
        assert transaction.amount == Decimal("7.5")
        assert transaction.description == "Added credits"
        session.add.assert_called_once_with(transaction)
