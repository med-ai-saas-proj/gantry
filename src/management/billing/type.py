import enum
from uuid import UUID
from typing import TypedDict
from decimal import Decimal
from datetime import datetime


class AggregatePeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BillingAggregateReport(TypedDict):
    period_bucket: datetime
    transaction_count: int
    total_amount: Decimal


class BillingTransactionInfo(TypedDict):
    amount: Decimal
    date: datetime
    organization_id: str
    transaction_uid: UUID
    project_uid: UUID
    details: dict
    captured_at: datetime | None
