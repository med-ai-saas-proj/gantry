from pyrusult import ResultStatus

from ..type import AggregatePeriod
from ..repositories.transaction_repo import TransactionRepository
from ..services.aggregate_query_service import BillingAggregateQueryService

import unittest
from uuid import uuid4
from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock


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
    def _make_service(self, repo):
        session = MagicMock()
        return (
            BillingAggregateQueryService(
                logger=MagicMock(),
                session_manager=_SessionManager(session),
                transaction_repo=repo,
            ),
            session,
        )

    # -- getAggregateSumByOrg --

    async def test_get_aggregate_by_org(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodFilterByOrganizations = AsyncMock(
            return_value=[{"total_amount": 1}]
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateSumByOrg(
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodFilterByOrganizations.assert_awaited_once_with(
            session,
            org_ids=["org1"],
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    # -- getAggregateSumByServices --

    async def test_get_aggregate_by_services(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodFilterByServiceName = AsyncMock(
            return_value=[
                {
                    "period_bucket": datetime(2026, 1, 1),
                    "transaction_count": 5,
                    "total_amount": 100,
                }
            ]
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateSumByServices(
            service_names=["gpt-4", "claude-3"],
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodFilterByServiceName.assert_awaited_once_with(
            session,
            service_names=["gpt-4", "claude-3"],
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    # -- getAggregateSumByProjects --

    async def test_get_aggregate_by_projects_all_org(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodFilterByProjects = AsyncMock(return_value=[])
        service, session = self._make_service(repo)

        res = await service.getAggregateSumByProjects(
            project_uuids=None,
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodFilterByProjects.assert_awaited_once_with(
            session,
            project_ids=[],
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    async def test_get_aggregate_by_projects_filtered(self):
        project_uuid = uuid4()
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodFilterByProjects = AsyncMock(return_value=[])
        service, session = self._make_service(repo)

        res = await service.getAggregateSumByProjects(
            project_uuids=[project_uuid],
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodFilterByProjects.assert_awaited_once_with(
            session,
            project_ids=ANY,
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    async def test_get_aggregate_by_projects_returns_error_for_unknown_projects(
        self,
    ):
        unknown = uuid4()
        repo = MagicMock(spec=TransactionRepository)
        service, session = self._make_service(repo)

        res = await service.getAggregateSumByProjects(
            project_uuids=[unknown],
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Err
        repo.sumByPeriodFilterByProjects.assert_not_called()

    # -- getAggregateGroupByOrgForAdmin --

    async def test_get_aggregate_group_by_org_for_admin_without_org_ids(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodGroupedByOrganizations = AsyncMock(return_value=[])
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByOrgAll(
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodGroupedByOrganizations.assert_awaited_once_with(
            session,
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
            org_ids=None,
        )

    async def test_get_aggregate_group_by_org_for_admin_with_org_ids(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodGroupedByOrganizations = AsyncMock(return_value=[])
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByOrgAll(
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 2, 1, tzinfo=UTC),
            aggregate_period=AggregatePeriod.DAILY,
            period_scale=1,
            org_ids=["org1", "org2"],
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodGroupedByOrganizations.assert_awaited_once_with(
            session,
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 2, 1),
            period=AggregatePeriod.DAILY,
            period_scale=1,
            org_ids=["org1", "org2"],
        )

    # -- getAggregateGroupByServiceForAdmin --

    async def test_get_aggregate_group_by_service_for_admin_without_org_ids(
        self,
    ):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodGroupedByServiceNameForAdmin = AsyncMock(
            return_value=[
                {
                    "period_bucket": datetime(2026, 1, 1),
                    "transaction_count": 10,
                    "total_amount": 500,
                    "service_name": "gpt-4",
                }
            ]
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByServiceAll(
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 2, 1, tzinfo=UTC),
            aggregate_period=AggregatePeriod.DAILY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodGroupedByServiceNameForAdmin.assert_awaited_once_with(
            session,
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 2, 1),
            period=AggregatePeriod.DAILY,
            period_scale=1,
            org_ids=None,
        )

    async def test_get_aggregate_group_by_service_for_admin_with_org_ids(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodGroupedByServiceNameForAdmin = AsyncMock(
            return_value=[
                {
                    "period_bucket": datetime(2026, 1, 1),
                    "transaction_count": 10,
                    "total_amount": 500,
                    "service_name": "gpt-4",
                }
            ]
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByServiceAll(
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 2, 1, tzinfo=UTC),
            aggregate_period=AggregatePeriod.DAILY,
            period_scale=1,
            org_ids=["org1", "org2"],
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodGroupedByServiceNameForAdmin.assert_awaited_once_with(
            session,
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 2, 1),
            period=AggregatePeriod.DAILY,
            period_scale=1,
            org_ids=["org1", "org2"],
        )

    # -- getAggregateGroupByService --

    async def test_get_aggregate_group_by_service(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodGroupedByServiceName = AsyncMock(
            return_value=[
                {
                    "period_bucket": datetime(2026, 1, 1),
                    "transaction_count": 10,
                    "total_amount": 500,
                    "service_name": "gpt-4",
                }
            ]
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByService(
            org_id="org1",
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=None,
            aggregate_period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

        assert res.status == ResultStatus.Ok
        repo.sumByPeriodGroupedByServiceName.assert_awaited_once_with(
            session,
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )

    # -- getAggregateGroupByServiceAndProject --

    async def test_get_aggregate_group_by_service_and_project(self):
        repo = MagicMock(spec=TransactionRepository)
        repo.sumByPeriodByServiceAndProjectGroupedByServiceAndProject = (
            AsyncMock(
                return_value=[
                    {
                        "period_bucket": datetime(2026, 1, 1),
                        "transaction_count": 3,
                        "total_amount": 150,
                        "service_name": "gpt-4",
                        "project_id": 1,
                        "project_uuid": uuid4(),
                        "project_name": "proj1",
                    }
                ]
            )
        )
        service, session = self._make_service(repo)

        res = await service.getAggregateGroupByServiceAndProject(
            service_names=None,
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
            service_names=None,
            project_ids=None,
            org_id="org1",
            start_time=datetime(2026, 1, 1),
            end_time=None,
            period=AggregatePeriod.MONTHLY,
            period_scale=1,
        )
