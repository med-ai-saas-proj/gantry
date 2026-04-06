from src.management.auth.entities import UserInfo
from src.management.auth.dependencies import getUserInfo
from src.shared.custom_types.responses import ListResponse

from ..type import AggregatePeriod, BillingAggregateReport
from .router import billing_router
from ..factories import getBillingAggregateQueryService
from ..services.aggregate_query_service import BillingAggregateQueryService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Query, Depends


@billing_router.get(
    "/aggregates/projects",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) and optional filters (e.g. project_id). Useful for dashboards, reports, etc.",
)
async def get_aggregate_by_projects(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
    project_uids: list[UUID] | None = Query(
        None
    ),  # filter by project_uid or whole organization
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.get_aggregate_by_projects(
            project_uids=project_uids,
            org_id=user_info["org_id"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/apikeys",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) and optional filters (e.g. apikey_id). Useful for dashboards, reports, etc.",
)
async def get_aggregate_by_apikeys(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
    apikeys: list[str] | None = Query(
        None
    ),  # filter by apikey_id or whole organization
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.get_aggregate_by_apikeys(
            apikeys=apikeys,
            org_id=user_info["org_id"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/organizations",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) for the whole organization. Useful for dashboards, reports, etc.",
)
async def get_aggregate_by_org(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.get_aggregate_by_org(
            org_id=user_info["org_id"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)
