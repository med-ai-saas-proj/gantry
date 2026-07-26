from .models import TransactionStatus, BillingSourceProvider

import enum
from uuid import UUID
from typing import TypedDict
from decimal import Decimal
from datetime import date, datetime


class AggregatePeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BillingAggregateReport(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal


class BillingAggregateReportGroupedByProject(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal
    project_int: int
    project_uuid: UUID
    project_name: str


class BillingAggregateReportGroupedByOrg(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal
    organization_id: str


class BillingAggregateReportGroupedByService(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal
    service_name: str


class BillingAggregateReportGroupedByServiceAndProject(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal
    service_name: str
    project_id: int
    project_uuid: UUID
    project_name: str


class BillingTransactionInfo(TypedDict):
    amount: Decimal
    date: datetime
    organization_id: str
    transaction_uid: UUID
    project_uuid: UUID
    details: dict
    captured_at: datetime | None
    status: TransactionStatus
    service_name: str


class BillingInvoiceInfo(TypedDict):
    invoice_id: int
    invoice_uid: UUID
    billing_period: date
    total_amount: Decimal
    provider: BillingSourceProvider | None
    provider_invoice_id: str | None
    paid_at: datetime | None
    details: dict
    used_credits: Decimal


class BillingInvoiceLineItemInfo(TypedDict):
    description: str
    amount: Decimal
    project_uuid: UUID | None
    invoice_line_uuid: UUID
    project_name: str | None
    project_id: int | None


class CreateBillingInvoiceLineItemInfo(TypedDict):
    description: str
    amount: Decimal
    project_id: int | None


class CreditTransactionInfo(TypedDict):
    amount: Decimal
    description: str
    created_at: datetime
