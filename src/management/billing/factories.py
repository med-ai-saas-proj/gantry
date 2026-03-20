"""Singleton factory for BillingService."""

from src.db.factories import getRedis, getSessionManager

from .services import BillingService
from .repositories import (
    SpendingLimitRepository,
)
from ...shared.logging.logger import getLogger

from functools import lru_cache


@lru_cache(1)
def getBillingService() -> BillingService:
    return BillingService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        redis=getRedis(),
        spending_limit_repo=SpendingLimitRepository(),
    )
