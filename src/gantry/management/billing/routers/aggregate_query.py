from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.management.project.factories import getProjectService
from gantry.shared.custom_types.responses import ListResponse
from gantry.management.project.permissions import ProjectPermission
from gantry.management.project.dependencies import assertProjectsRole
from gantry.management.organization.permissions import OrgPermission
from gantry.management.organization.dependencies import requiredOrgPermission

from ..dtos import ServiceProjectStatisticsResponse
from ..type import (
    AggregatePeriod,
    BillingAggregateReport,
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
    "/aggregates/projects",
    description="Aggregate usage costs across one or more projects within your organization, bucketed by the specified time period. When no project UUIDs are provided, defaults to all projects the user has access to. Returns one entry per time bucket with the summed cost.",
)
async def get_aggregate_sum_by_projects(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # inclusive start of the aggregation window, ISO 8601 (e.g. "2024-01-01")
    period_end: datetime,  # exclusive end of the aggregation window, ISO 8601 (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # number of native period units per bucket (e.g. period=DAILY, scale=2 → 2-day buckets)
    project_uuids: list[UUID] | None = Query(
        None
    ),  # restrict to specific project UUIDs; if omitted, all accessible projects are included
) -> ListResponse[BillingAggregateReport]:
    project_uids_set = (
        [str(uid) for uid in project_uuids] if project_uuids else []
    )
    if project_uids_set:
        await assertProjectsRole(
            project_service=getProjectService(),
            user_info=user_info,
            project_uuids=project_uids_set,
            required_permissions=[ProjectPermission.MEMBER],
        )
        project_uids = [UUID(uid) for uid in project_uids_set]
    else:
        project_uids = [
            UUID(uid) for uid in user_info["project_permissions"].keys()
        ]

    res = (
        await billing_service.getAggregateSumByProjects(
            project_uuids=project_uids,
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/organizations",
    description="Aggregate usage costs for the entire organization, bucketed by the specified time period. Returns one entry per time bucket with the summed cost across all projects and services in the org.",
)
async def get_aggregate_sum_by_org(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # inclusive start of the aggregation window, ISO 8601
    period_end: datetime,  # exclusive end of the aggregation window, ISO 8601
    period: AggregatePeriod,
    period_scale: int = 1,  # number of native period units per bucket
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.getAggregateSumByOrg(
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/services",
    description="Aggregate usage costs across specified service names within your organization, bucketed by the specified time period. Returns one entry per time bucket with the summed cost. When no service names are provided, all services are included.",
)
async def get_aggregate_sum_by_services(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    service_names: list[str] = Query(default=[]),
) -> ListResponse[BillingAggregateReport]:
    res = (
        await billing_service.getAggregateSumByServices(
            service_names=service_names,
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/grouped-by-service-and-project",
    description="Aggregate usage costs grouped by (service name, project) within your organization, bucketed by the specified time period. Returns per-service and per-project breakdowns one row at a time, allowing callers to reconstruct a grid of service × project costs.",
)
async def get_aggregate_grouped_by_service_and_project(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
    service_names: list[str] = Query(default=[]),
    project_uuids: list[UUID] | None = Query(None),
) -> ListResponse[ServiceProjectStatisticsResponse]:
    project_uids_set = (
        [str(uid) for uid in project_uuids] if project_uuids else []
    )
    if project_uids_set:
        await assertProjectsRole(
            project_service=getProjectService(),
            user_info=user_info,
            project_uuids=project_uids_set,
            required_permissions=[ProjectPermission.MEMBER],
        )
        project_uids = [UUID(uid) for uid in project_uids_set]
    else:
        project_uids = None

    res = (
        await billing_service.getAggregateGroupByServiceAndProject(
            service_names=service_names if service_names else None,
            project_uuids=project_uids,
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[ServiceProjectStatisticsResponse](data=res)


@billing_router.get(
    "/aggregates/grouped-by-services",
    description="Aggregate usage costs grouped by service name within your organization, bucketed by the specified time period. Returns one entry per time bucket per service, with each entry containing the total cost for that service.",
)
async def get_aggregate_grouped_by_service(
    user_info: Annotated[
        UserInfo,
        Depends(requiredOrgPermission(OrgPermission.BILLING_VIEW_USAGE)),
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,
    period_end: datetime,
    period: AggregatePeriod,
    period_scale: int = 1,
) -> ListResponse[BillingAggregateReportGroupedByService]:
    res = (
        await billing_service.getAggregateGroupByService(
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReportGroupedByService](data=res)
