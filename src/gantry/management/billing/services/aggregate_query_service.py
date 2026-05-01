from gantry.db.session import AsyncSessionManager
from gantry.management.api_key import ApiKeyService, InvalidAPIKey
from gantry.management.project import Project, ProjectNotFoundError

from ..type import AggregatePeriod, BillingAggregateReport
from ..repositories.transaction_repo import TransactionRepository

from uuid import UUID
from typing import Any, Sequence
from datetime import UTC, datetime

from pyrusult import Ok, Err, Result, ResultStatus
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

    async def get_aggregate_by_projects(
        self,
        project_uids: list[UUID] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        aggregate_period: AggregatePeriod,
        period_scale: int,
    ) -> Result[Sequence[BillingAggregateReport], ProjectNotFoundError]:
        """Fetch the current total_amount for the given project/org/period."""
        if project_uids is not None and len(project_uids) > 0:
            async with self.session_manager.get_session() as session:
                projs_info_res = await session.execute(
                    select(Project.id, Project.uuid).where(
                        Project.uuid.in_(project_uids),
                        Project.organization_id == org_id,
                    )
                )
                projs_info = {row.uuid: row.id for row in projs_info_res.all()}
                project_ids = list(projs_info.values())
                existed_project_uids = set(projs_info.keys())
                missing_project_uids = set(project_uids) - existed_project_uids
                if missing_project_uids:
                    return Err(
                        ProjectNotFoundError(
                            message=f"Project UUIDs not found: {', '.join(str(uid) for uid in missing_project_uids)}"
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

    async def get_aggregate_by_apikeys(
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

    async def get_aggregate_by_org(
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
