"""Singleton factory for BillingService."""

from src.db.factories import getRedis, getSessionManager

from .settings import getBillingSourceSetting
from ..api_keys.factories import getApiKeyService
from ...shared.logging.logger import getLogger
from .services.billing_source_service import (
    BillingSourceService,
)
from .repositories.billing_source_repo import (
    BillingSourceRepo,
)
from .repositories.spending_limit_repo import SpendingLimitRepository
from .services.aggregate_query_service import BillingAggregateQueryService
from .repositories.billing_transaction_repo import BillingTransactionRepository
from .services.billing_transaction_services import BillingTransactionService

from functools import lru_cache

from stripe import StripeClient


@lru_cache(1)
def getBillingTransactionService() -> BillingTransactionService:
    return BillingTransactionService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        redis=getRedis(),
        spending_limit_repo=SpendingLimitRepository(),
        billing_transaction_repo=BillingTransactionRepository(),
        apikey_service=getApiKeyService(),
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
