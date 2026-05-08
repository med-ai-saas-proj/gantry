from gantry.management.auth.roles import ManagementRole
from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.shared.custom_types.responses import ListResponse

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
    user_info: Annotated[
        UserInfo, Depends(requireRole(ManagementRole.BILLING_VIEW_USAGE))
    ],
    billing_service: Annotated[
        BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
    ],
    period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
    period: AggregatePeriod,
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
    project_uuids: list[UUID] | None = Query(
        None
    ),  # filter by project_uuid or whole organization
) -> ListResponse[BillingAggregateReport]:
    project_uids_set = (
        set([str(uid) for uid in project_uids]) if project_uids else set()
    )
    if project_uids_set:
        check_access_to_projects(
            user_info=user_info, project_uids=project_uids_set
        )
        project_uids = [UUID(uid) for uid in project_uids_set]
    else:  # if no project_uids filter provided, default to all projects user has access to
        project_uids = [UUID(uid) for uid in user_info["project_uids"]]

    res = (
        await billing_service.get_aggregate_by_projects(
            project_uuids=project_uuids,
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)


# NOTE: frontend can't call this endpoint due to api key can't show again in the UI after it's created and it without uuid
# so we can't let users filter by apikeys.
# @billing_router.get(
#     "/aggregates/apikeys",
#     description="Get aggregated billing data for a given period (e.g. daily, monthly) and optional filters (e.g. apikey_id). Useful for dashboards, reports, etc.",
# )
# async def get_aggregate_by_apikeys(
#     user_info: Annotated[UserInfo, Depends(getUserInfo)],
#     billing_service: Annotated[
#         BillingAggregateQueryService, Depends(getBillingAggregateQueryService)
#     ],
#     period_start: datetime,  # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
#     period_end: datetime,  # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
#     period: AggregatePeriod,
#     period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
#     apikeys: list[str] | None = Query(
#         None
#     ),  # filter by apikey_id or whole organization
# ) -> ListResponse[BillingAggregateReport]:
#     res = (
#         await billing_service.get_aggregate_by_apikeys(
#             apikeys=apikeys,
#             org_id=user_info["org_id"],
#             start_time=period_start,
#             end_time=period_end,
#             aggregate_period=period,
#             period_scale=period_scale,
#         )
#     ).unwrap()
#     return ListResponse[BillingAggregateReport](data=res)


@billing_router.get(
    "/aggregates/organizations",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) for the whole organization. Useful for dashboards, reports, etc.",
)
async def get_aggregate_by_org(
    user_info: Annotated[
        UserInfo, Depends(requireRole(ManagementRole.BILLING_VIEW_USAGE_ALL))
    ],
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
            org_id=user_info["org_uuid"],
            start_time=period_start,
            end_time=period_end,
            aggregate_period=period,
            period_scale=period_scale,
        )
    ).unwrap()
    return ListResponse[BillingAggregateReport](data=res)
