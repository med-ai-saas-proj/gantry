from ..models import TransactionStatus
from .transaction_services import TransactionService, TransactionNotFound
from ..repositories.transaction_repo import TransactionRepository

import unittest
from uuid import uuid4
from types import SimpleNamespace
from typing import Any, cast
from decimal import Decimal
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from pyrusult import Ok, ResultStatus


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


class TransactionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_transactions_maps_repo_rows(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.getTransactionInfoList = AsyncMock(
            return_value=(
                [
                    {
                        "transaction_uid": uuid4(),
                        "project_uuid": uuid4(),
                        "amount": Decimal("10.5"),
                        "details": {"x": 1},
                        "date": datetime(2026, 1, 15),
                        "captured_at": None,
                        "status": TransactionStatus.PENDING,
                    }
                ],
                1,
            )
        )
        session_manager = cast(Any, _SessionManager(session))
        service = TransactionService(
            logger=MagicMock(),
            session_manager=session_manager,
            redis=MagicMock(),
            org_settings_repo=MagicMock(),
            project_settings_repo=MagicMock(),
            transaction_repo=repo,
        )

        transactions, total = await service.getTransactions("org1")

        assert total == 1
        assert transactions[0].amount == Decimal("10.5")

    async def test_get_transaction_by_id_returns_err_when_missing(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.getTransactionInfoByUUID = AsyncMock(return_value=None)
        session_manager = cast(Any, _SessionManager(session))
        service = TransactionService(
            logger=MagicMock(),
            session_manager=session_manager,
            redis=MagicMock(),
            org_settings_repo=MagicMock(),
            project_settings_repo=MagicMock(),
            transaction_repo=repo,
        )

        res = await service.getTransactionById("org1", uuid4())

        assert res.status == ResultStatus.Err
        assert isinstance(res.err(), TransactionNotFound)

    async def test_get_spending_limits_converts_scaled_values(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        session_manager = cast(Any, _SessionManager(session))
        service = TransactionService(
            logger=MagicMock(),
            session_manager=session_manager,
            redis=MagicMock(),
            org_settings_repo=MagicMock(),
            project_settings_repo=MagicMock(),
            transaction_repo=repo,
        )
        service._getOrLoadSpendingLimitsToRedis = AsyncMock(
            return_value=Ok(("100000000", "250000000"))
        )

        res = await service.getSpendingLimits("org1", 12)

        assert res.status == ResultStatus.Ok
        project_limit, org_limit = res.unwrap()
        assert project_limit == Decimal("2.5")
        assert org_limit == Decimal("1")

    async def test_close_expired_transactions_logs_count(self):
        session = MagicMock()
        session.expunge_all = MagicMock()
        session.commit = AsyncMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.setTransactionsExpired = AsyncMock(
            return_value=[SimpleNamespace(uuid=uuid4())]
        )
        logger = MagicMock()
        session_manager = cast(Any, _SessionManager(session))
        service = TransactionService(
            logger=logger,
            session_manager=session_manager,
            redis=MagicMock(),
            org_settings_repo=MagicMock(),
            project_settings_repo=MagicMock(),
            transaction_repo=repo,
        )

        await service.closeExpiredTransactions(uuid4(), datetime(2026, 1, 15))

        logger.info.assert_called()
