from .dtos import ScaledAmount

from decimal import Decimal
from datetime import datetime


def get_billing_period(
    ref_time: datetime,
) -> datetime:
    """Return the current UTC billing period in YYYY-MM format."""
    return ref_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_next_billing_period(current_period: datetime) -> datetime:
    """Return the next UTC billing period in YYYY-MM format."""
    if current_period.month == 12:
        return current_period.replace(year=current_period.year + 1, month=1)
    else:
        return current_period.replace(month=current_period.month + 1)


def get_previous_billing_period(current_period: datetime) -> datetime:
    """Return the previous UTC billing period in YYYY-MM format."""
    if current_period.month == 1:
        return current_period.replace(year=current_period.year - 1, month=12)
    else:
        return current_period.replace(month=current_period.month - 1)
