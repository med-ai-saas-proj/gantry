from pyrusult import Ok, ResultStatus

from ..type import AggregatePeriod
from ..repositories.transaction_repo import TransactionRepository
from ..services.aggregate_query_service import BillingAggregateQueryService

import unittest
from uuid import uuid4
from types import SimpleNamespace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock


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

        res = await service.getAggregateSumByOrg(
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodByOrganizations.assert_awaited_once()

    async def test_get_aggregate_by_service_name_calls_repo(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodByServiceName = AsyncMock(
            return_value=[
                {
                    "period_bucket": datetime(2026, 1, 1),
                    "transaction_count": 5,
                    "total_amount": 100,
                }
            ]
        )
        logger = MagicMock()
        service = BillingAggregateQueryService(
            logger=logger,
            session_manager=_SessionManager(session),
            transaction_repo=repo,
            apikey_service=MagicMock(),
        )

        res = await service.getAggregateSumByServiceName(
            service_names=["gpt-4", "claude-3"],
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodByServiceName.assert_awaited_once_with(
            session,
            service_names=["gpt-4", "claude-3"],
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    async def test_get_aggregate_by_service_and_project_calls_repo(self):
        session = MagicMock()
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodByServiceAndProjectGroupedByServiceAndProject = (
            AsyncMock(return_value=[])
        )
        logger = MagicMock()
        service = BillingAggregateQueryService(
            logger=logger,
            session_manager=_SessionManager(session),
            transaction_repo=repo,
            apikey_service=MagicMock(),
        )

        res = await service.getAggregateGroupByAndSumByServiceAndProject(
            service_names=["gpt-4"],
            project_uuids=None,
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodByServiceAndProjectGroupedByServiceAndProject.assert_awaited_once_with(
            session,
            service_names=["gpt-4"],
            project_ids=None,
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )
