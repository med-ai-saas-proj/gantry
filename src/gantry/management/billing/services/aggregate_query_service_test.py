from ..type import AggregatePeriod
from ..repositories.transaction_repo import TransactionRepository
from ..services.aggregate_query_service import BillingAggregateQueryService

import unittest
from uuid import uuid4
from types import SimpleNamespace
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


class AggregateQueryServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_aggregate_by_org_calls_repo_with_org_id(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodByOrganizations = AsyncMock(
            return_value=[{"total_amount": 1}]
        )
        logger = MagicMock()
        service = BillingAggregateQueryService(
            logger=logger,
            session_manager=_SessionManager(session),
            transaction_repo=repo,
            apikey_service=MagicMock(),
        )

        res = await service.getAggregateByOrg(
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodByOrganizations.assert_awaited_once()

    async def test_get_aggregate_by_apikeys_uses_api_key_service(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodByApiKeys = AsyncMock(
            return_value=[{"total_amount": 1}]
        )
        apikey_service = MagicMock()
        apikey_service.getApiKeysInfo = AsyncMock(
            return_value=Ok([{"api_key_id": 7}])
        )
        logger = MagicMock()
        service = BillingAggregateQueryService(
            logger=logger,
            session_manager=_SessionManager(session),
            transaction_repo=repo,
            apikey_service=apikey_service,
        )

        res = await service.getAggregateByApikeys(
            apikeys=[str(uuid4())],
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        apikey_service.getApiKeysInfo.assert_awaited_once()
        repo.sumByPeriodByApiKeys.assert_awaited_once()
