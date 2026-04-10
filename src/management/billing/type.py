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


class BillingAggregateReportGroupedBy(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal
    group_by_uuid_key: UUID | str
    group_by_int_key: int
    group_by_name: str | None


class BillingTransactionInfo(TypedDict):
    amount: Decimal
    date: datetime
    organization_id: str
    transaction_uid: UUID
    project_uid: UUID
    details: dict
    captured_at: datetime | None


class BillingInvoiceInfo(TypedDict):
    invoice_id: int
    invoice_uid: UUID
    billing_period: date
    total_amount: Decimal
    provider_invoice_id: str | None
    paid_at: datetime | None
    details: dict
    used_credits: Decimal


class BillingInvoiceLineItemInfo(TypedDict):
    description: str
    amount: Decimal
    project_uid: UUID | None
    invoice_line_uuid: UUID
    project_name: str | None
    project_id: int | None


class CreateBillingInvoiceLineItemInfo(TypedDict):
    description: str
    amount: Decimal
    project_id: int | None
