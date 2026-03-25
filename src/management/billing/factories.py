"""Singleton factory for BillingService."""

from src.db.factories import getRedis, getSessionManager
from src.management.billing.settings import getBillingSourceSetting
from src.management.billing.services.billing_source_service import (
    BillingSourceService,
)
from src.management.billing.repositories.billing_source_repo import (
    BillingSourceRepo,
)

from .services.services import BillingService
from ..api_keys.factories import getApiKeyService
from ...shared.logging.logger import getLogger
from .repositories.spending_limit_repo import SpendingLimitRepository
from .services.aggregate_query_services import BillingAggregateQueryService
from .repositories.billing_transaction_repo import BillingTransactionRepository

from functools import lru_cache

from httpx import get
from stripe import StripeClient


@lru_cache(1)
def getBillingService() -> BillingService:
    return BillingService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        redis=getRedis(),
        spending_limit_repo=SpendingLimitRepository(),
        billing_transaction_repo=BillingTransactionRepository(),
    )


@lru_cache(1)
def getBillingSourceService() -> BillingSourceService:
    billing_source_settings = getBillingSourceSetting()
    return BillingSourceService(
        billing_source_repo=BillingSourceRepo(),
        session_manager=getSessionManager(),
        stripe_client=StripeClient(
            billing_source_settings.stripe_secret_key.get_secret_value()
        ),
    )


@lru_cache(1)
def getBillingAggregateQueryService() -> BillingAggregateQueryService:
    return BillingAggregateQueryService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        billing_transaction_repo=BillingTransactionRepository(),
        apikey_service=getApiKeyService(),
    )
