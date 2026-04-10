from gantry.db.factories import getSessionManager
from gantry.management.billing.type import AggregatePeriod
from gantry.shared.utils.uuid_utils import uuid7
from gantry.management.billing.repositories.transaction_repo import (
    TransactionRepository,
)

import unittest
from decimal import Decimal
from datetime import datetime


class TestAuthDependencies(unittest.IsolatedAsyncioTestCase):
    async def test_timescaledb(self):

        async with getSessionManager().get_session() as session:
            repo = TransactionRepository()
            await repo.addTransaction(
                session=session,
                transaction_uid=uuid7(),
                apikey_id=1,
                project_id=1,
                org_id="org1",
                amount=Decimal("10.5"),
                details={"example": "data"},
                created_at=datetime(2026, 1, 15),
            )
            await repo.addTransaction(
                session=session,
                transaction_uid=uuid7(),
                apikey_id=2,
                project_id=1,
                org_id="org1",
                amount=Decimal("20.0"),
                details={"example": "data"},
                created_at=datetime(2026, 1, 20),
            )
            await session.commit()
        async with getSessionManager().get_session() as session:
            transactions = await repo.sumByPeriodByApiKeys(
                session=session,
                apikey_ids=[1, 2, 3],
                org_id="org1",
                start_time=datetime(2026, 1, 1),
                end_time=datetime(2026, 12, 31),
                period=AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            print(transactions)
