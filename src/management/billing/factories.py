"""Singleton factory for BillingService."""

from src.db.factories import (
    getRedis,
    getSessionManager,
    getTimescaleSessionManager,
)

from .settings import getBillingSourceSetting
from ..api_keys.factories import getApiKeyService
from ...shared.logging.logger import getLogger
from .services.invoice_service import InvoiceService
from .repositories.invoice_repo import InvoiceRepo
from .repositories.transaction_repo import TransactionRepository
from .services.transaction_services import TransactionService
from .services.billing_source_service import (
    BillingSourceService,
)
from .repositories.billing_source_repo import (
    BillingSourceRepo,
)
from .repositories.spending_limit_repo import SpendingLimitRepository
from .services.aggregate_query_service import BillingAggregateQueryService

from functools import lru_cache

from stripe import StripeClient


@lru_cache(1)
def getBillingTransactionService() -> TransactionService:
    return TransactionService(
        logger=getLogger(),
        session_manager=getTimescaleSessionManager(),
        redis=getRedis(),
        spending_limit_repo=SpendingLimitRepository(),
        transaction_repo=TransactionRepository(),
        apikey_service=getApiKeyService(),
    )


@lru_cache(1)
def getBillingSourceService() -> BillingSourceService:
    billing_source_settings = getBillingSourceSetting()
    return BillingSourceService(
        billing_source_repo=BillingSourceRepo(),
        session_manager=getTimescaleSessionManager(),
        stripe_client=StripeClient(
            billing_source_settings.stripe_secret_key.get_secret_value()
        ),
    )


@lru_cache(1)
def getBillingAggregateQueryService() -> BillingAggregateQueryService:
    return BillingAggregateQueryService(
        logger=getLogger(),
        timescale_session_manager=getTimescaleSessionManager(),
        transaction_repo=TransactionRepository(),
        apikey_service=getApiKeyService(),
        session_manager=getSessionManager(),
    )


@lru_cache(1)
def getInvoiceService() -> InvoiceService:
    return InvoiceService(
        session_manager=getTimescaleSessionManager(),
        invoice_repo=InvoiceRepo(),
    )
