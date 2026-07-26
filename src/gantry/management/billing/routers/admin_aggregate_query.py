from gantry.management.auth.entities import AdminInfo
from gantry.management.auth.dependencies import getAdminInfo
from gantry.shared.custom_types.responses import ListResponse

from ..dtos import ServiceProjectStatisticsResponse
from ..type import (
    AggregatePeriod,
    BillingAggregateReport,
    BillingAggregateReportGroupedByOrg,
    BillingAggregateReportGroupedByService,
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
    description="Aggregate usage costs across one or more projects in a specified organization, bucketed by the specified time period. When no project UUIDs are provided, all projects in the org are included. Returns one entry per time bucket with the summed cost.",
    tags=["admin"],
)
async def get_aggregate_sum_by_projects(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,  # inclusive start of the aggregation window, ISO 8601
    period_end: datetime,  # exclusive end of the aggregation window, ISO 8601
    period: AggregatePeriod,
    period_scale: int = 1,  # number of native period units per bucket
    project_uuids: list[UUID] | None = Query(
        None
    ),  # restrict to specific project UUIDs; if omitted, all projects in the org are included
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
    description="Aggregate usage costs for an entire organization, bucketed by the specified time period. Returns one entry per time bucket with the summed cost across all projects and services in the org.",
    tags=["admin"],
)
async def get_aggregate_sum_by_org(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    org_id: str,
    period_start: datetime,  # inclusive start of the aggregation window, ISO 8601
    period_end: datetime,  # exclusive end of the aggregation window, ISO 8601
    period: AggregatePeriod,
    period_scale: int = 1,  # number of native period units per bucket
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
    description="Aggregate usage costs across specified service names in a given organization, bucketed by the specified time period. When no service names are provided, all services are included. Returns one entry per time bucket with the summed cost.",
    tags=["admin"],
)
async def get_aggregate_sum_by_services(
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
        await billing_service.getAggregateSumByServices(
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
    "/admin/aggregates/grouped-by-service-and-project",
    description="Aggregate usage costs grouped by (service name, project) within a given organization, bucketed by the specified time period. Returns per-service and per-project breakdowns one row at a time, allowing callers to reconstruct a grid of service × project costs.",
    tags=["admin"],
)
async def get_aggregate_grouped_by_service_and_project(
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
        await billing_service.getAggregateGroupByServiceAndProject(
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


@billing_router.get(
    "/admin/aggregates/grouped-by-organizations",
    description="Aggregate usage costs grouped by organization, bucketed by the specified time period. Optionally filter by specific org IDs. Returns one entry per time bucket per org with the total cost for that org.",
    tags=["admin"],
)
async def get_aggregate_grouped_by_org(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    org_ids: list[str] = Query(default=[]),
) -> ListResponse[BillingAggregateReportGroupedByOrg]:
    res = (
        await billing_service.getAggregateGroupByOrgForAdmin(
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
            org_ids=org_ids if org_ids else None,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReportGroupedByOrg](data=res)


@billing_router.get(
    "/admin/aggregates/grouped-by-services",
    description="Aggregate usage costs grouped by service name, bucketed by the specified time period. Optionally filter by specific org IDs. Returns one entry per time bucket per service with the total cost for that service.",
    tags=["admin"],
)
async def get_aggregate_grouped_by_service(
    admin_info: Annotated[AdminInfo, Depends(getAdminInfo)],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    org_ids: list[str] = Query(default=[]),
) -> ListResponse[BillingAggregateReportGroupedByService]:
    res = (
        await billing_service.getAggregateGroupByServiceForAdmin(
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
            org_ids=org_ids if org_ids else None,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReportGroupedByService](data=res)
