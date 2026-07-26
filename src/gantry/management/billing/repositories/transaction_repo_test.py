from gantry.shared.utils.uuid_utils import uuid7

from ..type import AggregatePeriod
from ..models import TransactionStatus
from .transaction_repo import TransactionRepository

import unittest
from types import SimpleNamespace
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


class TransactionRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_transaction_builds_pending_model_without_db(self):
        session = MagicMock()
        session.flush = AsyncMock()
        repo = TransactionRepository()
        transaction_uid = uuid7()
        created_at = datetime(2026, 1, 15)

        tx = await repo.addTransaction(
            session=session,
            transaction_uid=transaction_uid,
            apikey_id=1,
            project_id=2,
            org_id="org1",
            amount=Decimal("10.5"),
            details={"example": "data"},
            created_at=created_at,
            service_name="gpt-4",
        )

        assert tx.uuid == transaction_uid
        assert tx.apikey_id == 1
        assert tx.project_id == 2
        assert tx.organization_id == "org1"
        assert tx.amount == Decimal("10.5")
        assert tx.details == {"example": "data"}
        assert tx.created_at == created_at
        assert tx.service_name == "gpt-4"
        assert tx.captured_at is None
        assert tx.status == TransactionStatus.PENDING
        session.add.assert_called_once_with(tx)
        session.flush.assert_awaited_once()

    async def test_add_transaction_can_mark_captured_without_db(self):
        session = MagicMock()
        session.flush = AsyncMock()
        repo = TransactionRepository()

        tx = await repo.addTransaction(
            session=session,
            transaction_uid=uuid7(),
            apikey_id=1,
            project_id=2,
            org_id="org1",
            amount=Decimal("10.5"),
            details={},
            created_at=datetime(2026, 1, 15),
            service_name="gpt-4",
            capture=True,
        )

        assert tx.status == TransactionStatus.CAPTURED
        assert tx.captured_at is not None
        session.add.assert_called_once_with(tx)
        session.flush.assert_awaited_once()

    async def test_get_by_api_keys_short_circuits_empty_list_without_db(self):
        session = MagicMock()
        session.execute = AsyncMock()
        repo = TransactionRepository()

        assert await repo.getByApiKeys(session, [], org_id="org1") == []
        session.execute.assert_not_called()

    async def test_capture_transaction_returns_updated_row_without_db(self):
        tx = SimpleNamespace(uuid=uuid7(), amount=Decimal("10.5"))
        result = MagicMock()
        result.scalar_one_or_none.return_value = tx
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = TransactionRepository()

        captured = await repo.captureTransaction(
            session=session,
            transaction_uid=tx.uuid,
            real_amount=Decimal("11.25"),
        )

        assert captured is tx
        session.execute.assert_awaited_once()

    async def test_set_transactions_expired_returns_updated_rows_without_db(
        self,
    ):
        expired_tx = SimpleNamespace(uuid=uuid7())
        result = MagicMock()
        result.scalars.return_value.all.return_value = [expired_tx]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = TransactionRepository()

        expired = await repo.setTransactionsExpired(
            session=session,
            expiration_time=datetime(2026, 1, 1),
        )

        assert expired == [expired_tx]
        session.execute.assert_awaited_once()

    async def test_sum_by_period_by_service_and_project_maps_rows_without_db(
        self,
    ):
        result = MagicMock()
        result.all.return_value = [
            SimpleNamespace(
                period_bucket=datetime(2026, 1, 1),
                transaction_count=3,
                total_amount=Decimal("45.0"),
                service_name="gpt-4",
                project_id=42,
                project_uuid=uuid7(),
                project_name="my-project",
            ),
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = TransactionRepository()

        reports = (
            await repo.sumByPeriodByServiceAndProjectGroupedByServiceAndProject(
                session=session,
                service_names=["gpt-4"],
                project_ids=[42],
                org_id="org1",
                start_time=datetime(2026, 1, 1),
                end_time=datetime(2026, 12, 31),
                period=AggregatePeriod.MONTHLY,
                period_scale=1,
            )
        )

        assert reports == [
            {
                "period_bucket": datetime(2026, 1, 1),
                "transaction_count": 3,
                "total_amount": Decimal("45.0"),
                "service_name": "gpt-4",
                "project_id": 42,
                "project_uuid": result.all.return_value[0].project_uuid,
                "project_name": "my-project",
            },
        ]
        session.execute.assert_awaited_once()

    async def test_sum_by_period_by_service_name_maps_rows_without_db(self):
        result = MagicMock()
        result.all.return_value = [
            SimpleNamespace(
                period_bucket=datetime(2026, 1, 1),
                transaction_count=4,
                total_amount=Decimal("55.0"),
            ),
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        repo = TransactionRepository()

        reports = await repo.sumByPeriodFilterByServices(
            session=session,
            service_names=["gpt-4", "claude-3"],
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 12, 31),
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert reports == [
            {
                "period_bucket": datetime(2026, 1, 1),
                "transaction_count": 4,
                "total_amount": Decimal("55.0"),
            },
        ]
        session.execute.assert_awaited_once()
