"""Singleton factory for BillingService."""

from src.db.factories import (
    getRedis,
    getSessionManager,
)

from .settings import getBillingSetting
from ..api_keys.factories import getApiKeyService
from ...shared.logging.logger import getLogger
from .repositories.credit_repo import CreditRepo
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
        session_manager=getSessionManager(),
        redis=getRedis(),
        spending_limit_repo=SpendingLimitRepository(),
        transaction_repo=TransactionRepository(),
        apikey_service=getApiKeyService(),
    )


@lru_cache(1)
def getStripeClient() -> StripeClient:
    billing_source_settings = getBillingSetting()
    return StripeClient(
        billing_source_settings.stripe_secret_key.get_secret_value()
    )


@lru_cache(1)
def getBillingSourceService() -> BillingSourceService:
    return BillingSourceService(
        billing_source_repo=BillingSourceRepo(),
        session_manager=getSessionManager(),
        stripe_client=getStripeClient(),
        redis_client=getRedis(),
    )


@lru_cache(1)
def getBillingAggregateQueryService() -> BillingAggregateQueryService:
    return BillingAggregateQueryService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        transaction_repo=TransactionRepository(),
        apikey_service=getApiKeyService(),
    )


@lru_cache(1)
def getInvoiceService() -> InvoiceService:
    return InvoiceService(
        logger=getLogger(),
        session_manager=getSessionManager(),
        invoice_repo=InvoiceRepo(),
        transaction_repo=TransactionRepository(),
        billing_source_repo=BillingSourceRepo(),
        stripe_client=getStripeClient(),
        credit_repo=CreditRepo(),
    )
