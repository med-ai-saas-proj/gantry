"""Singleton factory for BillingService."""

from src.db.factories import getRedis, getSessionManager
from src.shared.utils.logger import getLogger

from .services import BillingService
from .repositories import (
    MonthlyAggregateRepository,
    ProjectSpendingLimitRepository,
    SpendingLimitRepository,
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
        spending_limit_repo=SpendingLimitRepository(),
    )
