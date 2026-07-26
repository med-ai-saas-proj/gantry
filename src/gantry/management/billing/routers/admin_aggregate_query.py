from gantry.management.auth.entities import AdminInfo
from gantry.management.auth.dependencies import getAdminInfo
from gantry.shared.custom_types.responses import ListResponse

from ..dtos import ServiceProjectStatisticsResponse
from ..type import (
    AggregatePeriod,
    BillingAggregateReport,
)
from .router import billing_router
from ..factories import getBillingAggregateQueryService
from ..services.aggregate_query_service import BillingAggregateQueryService

from uuid import UUID
from typing import Annotated
from datetime import datetime

from fastapi import Query, Depends


@billing_router.get(
    "/admin/aggregates/projects",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) and optional filters (e.g. project_id). Useful for dashboards, reports, etc.",
    tags=["admin"],
)
async def get_aggregate_by_projects(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
    project_uuids: list[UUID] | None = Query(
        None
    ),  # filter by project_uuid or whole organization
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.getAggregateSumByProjects(
            project_uuids=project_uuids,
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
            org_id=org_id,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/admin/aggregates/organizations",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) for the whole organization. Useful for dashboards, reports, etc.",
    tags=["admin"],
)
async def get_aggregate_by_org(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.getAggregateSumByOrg(
            org_id=org_id,
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/admin/aggregates/services",
    description="Get aggregated billing data for a given period filtered by service names. Returns a single sum across all specified service names per time bucket. Useful for dashboards, reports, etc.",
    tags=["admin"],
)
async def get_aggregate_by_service_name(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    service_names: list[str] = Query(default=[]),
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.getAggregateSumByServiceName(
            service_names=service_names,
            org_id=org_id,
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/admin/aggregates/service-project-statistics",
    description="Get aggregated billing data grouped by service name and project for a given period. Supports optional filtering by service names and project UUIDs. Useful for dashboards, reports, etc.",
    tags=["admin"],
)
async def get_aggregate_by_service_and_project(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    service_names: list[str] = Query(default=[]),
    project_uuids: list[UUID] | None = Query(None),
) -> ListResponse[ServiceProjectStatisticsResponse]:
    res = (
        await billing_service.getAggregateGroupByAndSumByServiceAndProject(
            service_names=service_names if service_names else None,
            project_uuids=project_uuids,
            org_id=org_id,
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[ServiceProjectStatisticsResponse](data=res)
