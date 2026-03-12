"""Singleton factory for BillingService."""

from src.db.factories import getSessionManager, getRedis
from src.shared.utils.logger import getLogger

from .services import BillingService
from .repositories import (
    MonthlyAggregateRepository,
    ProjectSpendingLimitRepository,
    OrganizationSpendingLimitRepository,
)

from functools import lru_cache


@lru_cache(1)
def getBillingService() -> BillingService:
    return BillingService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        redis=getRedis(),
        monthly_agg_repo=MonthlyAggregateRepository(),
        project_limit_repo=ProjectSpendingLimitRepository(),
        org_limit_repo=OrganizationSpendingLimitRepository(),
    )
