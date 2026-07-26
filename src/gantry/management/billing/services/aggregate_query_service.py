from pyrusult import Ok, Err, Result
from gantry.db.session import AsyncSessionManager
from gantry.management.api_key import ApiKeyService, InvalidAPIKey
from gantry.management.project import Project, ProjectNotFoundError

from ..dtos import ServiceProjectStatisticsResponse
from ..type import (
    AggregatePeriod,
    BillingAggregateReport,
)
from ..repositories.transaction_repo import TransactionRepository

from uuid import UUID
from typing import Any, Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from structlog.stdlib import BoundLogger


class BillingAggregateQueryService:
    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        transaction_repo: TransactionRepository,
        apikey_service: ApiKeyService,
    ) -> None:
        self.logger = logger
        self.session_manager = session_manager
        self.billing_transaction_repo = transaction_repo
        self.apikey_service = apikey_service

    async def getAggregateSumByProjects(
        self,
        project_uuids: list[UUID] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], ProjectNotFoundError]:
        """Fetch the current total_amount for the given project/org/period."""
        if project_uuids is not None and len(project_uuids) > 0:
            async with self.session_manager.get_session() as session:
                projs_info_res = await session.execute(
                    select(Project.id, Project.uuid).where(
                        Project.uuid.in_(project_uuids),
                        Project.organization_id == org_id,
                    )
                )
                projs_info = {row.uuid: row.id for row in projs_info_res.all()}
                project_ids = list(projs_info.values())
                existed_project_uuids = set(projs_info.keys())
                missing_project_uuids = (
                    set(project_uuids) - existed_project_uuids
                )
                if missing_project_uuids:
                    return Err(
                        ProjectNotFoundError(
                            message=f"Project UUIDs not found: {', '.join(str(project_uuid) for project_uuid in missing_project_uuids)}"
                        )
                    )
        else:
            project_ids = []  # means aggregate for whole organization

        async with self.session_manager.get_session() as session:
            agg = (
                await self.billing_transaction_repo.sumByPeriodFilterByProjects(
                    session,
                    project_ids=project_ids,
                    org_id=org_id,
                    start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                    end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                    if end_time
                    else None,
                    period=aggregate_period,
                    period_scale=period_scale,
                )
            )
            return Ok(agg)

    async def getAggregateSumByOrg(
        self,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], Any]:
        """Fetch the current total_amount for the given org/period."""
        async with self.session_manager.get_session() as session:
            agg = await self.billing_transaction_repo.sumByPeriodFilterByOrganizations(
                session,
                org_ids=[org_id],
                start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                if end_time
                else None,
                period=aggregate_period,
                period_scale=period_scale,
            )
            return Ok(agg)

    async def getAggregateSumByServiceName(
        self,
        service_names: list[str],
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], None]:
        async with self.session_manager.get_session() as session:
            agg = await self.billing_transaction_repo.sumByPeriodFilterByServiceName(
                session,
                service_names=service_names,
                org_id=org_id,
                start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                if end_time
                else None,
                period=aggregate_period,
                period_scale=period_scale,
            )
            return Ok(agg)

    async def getAggregateGroupByAndSumByServiceAndProject(
        self,
        service_names: list[str] | None,
        project_uuids: list[UUID] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[ServiceProjectStatisticsResponse], None]:
        if project_uuids is not None and len(project_uuids) > 0:
            async with self.session_manager.get_session() as session:
                projs_info_res = await session.execute(
                    select(Project.id, Project.uuid).where(
                        Project.uuid.in_(project_uuids),
                        Project.organization_id == org_id,
                    )
                )
                project_ids = [row.id for row in projs_info_res.all()]
        else:
            project_ids = None

        async with self.session_manager.get_session() as session:
            agg = await self.billing_transaction_repo.sumByPeriodByServiceAndProjectGroupedByServiceAndProject(
                session,
                service_names=service_names,
                project_ids=project_ids,
                org_id=org_id,
                start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                if end_time
                else None,
                period=aggregate_period,
                period_scale=period_scale,
            )
            return Ok(
                [
                    ServiceProjectStatisticsResponse(
                        period_bucket=row["period_bucket"],
                        transaction_count=row["transaction_count"],
                        total_amount=row["total_amount"],
                        service_name=row["service_name"],
                        project_uuid=row["project_uuid"],
                        project_name=row["project_name"],
                    )
                    for row in agg
                ]
            )
