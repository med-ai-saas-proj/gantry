import enum
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
