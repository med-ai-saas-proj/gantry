from datetime import datetime
import enum
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.management.auth.entities import UserInfo
from ..factories import getBillingService
from src.management.auth.dependencies import getUserInfo
from src.management.auth.entities import UserInfo
from ..services import BillingService

from .router import billing_router

class AggregatePeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@billing_router.get(
    "/aggregates",
    description="Get aggregated billing data for a given period (e.g. daily, monthly) and optional filters (e.g. project_id). Useful for dashboards, reports, etc."
)
async def get_aggregates(
    period: AggregatePeriod,
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    billing_service: Annotated[BillingService, Depends(getBillingService)],
    period_scale: int = 1,  # e.g. if period=DAILY and period_scale=2 -> aggregate by 2 days
    project_uid: list[UUID] | None = None, # filter by project_uid or whole organization
    period_start: datetime | None = None, # ISO date string to specify the start of the aggregation period (e.g. "2024-01-01")
    period_end: datetime | None = None, # ISO date string to specify the end of the aggregation period (e.g. "2024-01-31")
):
    pass