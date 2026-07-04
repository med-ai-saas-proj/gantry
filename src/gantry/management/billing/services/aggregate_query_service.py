from pyrusult import Ok, Err, Result, ResultStatus
from gantry.db.session import AsyncSessionManager
from gantry.management.api_key import ApiKeyService, InvalidAPIKey
from gantry.management.project import Project, ProjectNotFoundError

from ..type import AggregatePeriod, BillingAggregateReport
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

    async def getAggregateByProjects(
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
            agg = await self.billing_transaction_repo.sumByPeriodByProjects(
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
            return Ok(agg)

    async def getAggregateByApikeys(
        self,
        apikeys: list[str] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], InvalidAPIKey]:
        """Fetch the current total_amount for the given apikey/org/period."""
        if apikeys is not None and len(apikeys) > 0:
            apikeys_info_res = await self.apikey_service.getApiKeysInfo(apikeys)
            if apikeys_info_res.status == ResultStatus.Err:
                return apikeys_info_res.into()
            apikey_ids = [
                info["api_key_id"] for info in apikeys_info_res.unwrap()
            ]
        else:
            apikey_ids = []  # means aggregate for whole organization
        async with self.session_manager.get_session() as session:
            agg = await self.billing_transaction_repo.sumByPeriodByApiKeys(
                session,
                apikey_ids=apikey_ids,
                org_id=org_id,
                start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                if end_time
                else None,
                period=aggregate_period,
                period_scale=period_scale,
            )
            return Ok(agg)

    async def getAggregateByOrg(
        self,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], Any]:
        """Fetch the current total_amount for the given org/period."""
        async with self.session_manager.get_session() as session:
            agg = (
                await self.billing_transaction_repo.sumByPeriodByOrganizations(
                    session,
                    org_ids=[org_id],
                    start_time=start_time.astimezone(UTC).replace(tzinfo=None),
                    end_time=end_time.astimezone(UTC).replace(tzinfo=None)
                    if end_time
                    else None,
                    period=aggregate_period,
                    period_scale=period_scale,
                )
            )
            return Ok(agg)
