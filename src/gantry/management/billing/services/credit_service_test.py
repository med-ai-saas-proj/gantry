from .credit_service import CreditService
from ..repositories.credit_repo import CreditRepo

import unittest
from types import SimpleNamespace
from typing import Any, cast
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from pyrusult import ResultStatus


class _AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionManager:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return _AsyncContextManager(self.session)


class CreditServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_available_credits_returns_zero_when_missing(self):
        session = MagicMock()
        repo = MagicMock(spec=CreditRepo)
        repo.getCreditByOrgId = AsyncMock(return_value=None)
        session_manager = cast(Any, _SessionManager(session))
        service = CreditService(session_manager, repo)

        assert await service.getAvailableCredits("org1") == Decimal(0)

    async def test_add_credits_calls_repo_and_commits(self):
        session = MagicMock()
        session.begin = MagicMock(return_value=_AsyncContextManager(None))
        session.commit = AsyncMock()
        repo = MagicMock(spec=CreditRepo)
        repo.addCreditForOrg = AsyncMock(
            return_value=SimpleNamespace(amount=Decimal("12.5"))
        )
        repo.createCreditTransaction = AsyncMock()
        session_manager = cast(Any, _SessionManager(session))
        service = CreditService(session_manager, repo)

        amount = await service.addCredits(
            "org1",
            {"value": 1250000000, "scale": 8},
            description="Added credits",
        )

        assert amount == Decimal("12.5")
        repo.addCreditForOrg.assert_awaited_once()
        repo.createCreditTransaction.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_add_credits_rejects_non_positive_amount(self):
        session = MagicMock()
        session_manager = cast(Any, _SessionManager(session))
        service = CreditService(session_manager, MagicMock(spec=CreditRepo))

        with self.assertRaises(ValueError):
            await service.addCredits("org1", {"value": 0, "scale": 8})

    async def test_get_credit_transactions_maps_response(self):
        session = MagicMock()
        repo = MagicMock(spec=CreditRepo)
        repo.getCreditTransactions = AsyncMock(
            return_value=(
                [
                    {
                        "amount": Decimal("5.0"),
                        "description": "Added credits",
                        "created_at": datetime(2026, 1, 15),
                    }
                ],
                1,
            )
        )
        session_manager = cast(Any, _SessionManager(session))
        service = CreditService(session_manager, repo)

        transactions, total = await service.getCreditTransactions("org1")

        assert total == 1
        assert transactions[0].amount == Decimal("5.0")
