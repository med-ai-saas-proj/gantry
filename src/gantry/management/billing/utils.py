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


def scaled_amount_to_decimal(amount: ScaledAmount) -> Decimal:
    """Convert a ScaledAmount to a Python Decimal.

    Decimal.scaleb(n) multiplies by 10^n — exact integer arithmetic, no float.
    """
    return Decimal(amount["value"]).scaleb(-amount["scale"])


def decimal_to_scaled_int(amount: Decimal, scale: int) -> int:
    """Convert a Decimal amount to an integer representation given a scale."""
    return int((amount * (10**scale)).to_integral_value())


def scaled_int_to_decimal(amount: int, scale: int) -> Decimal:
    """Convert an integer amount with scale back to Decimal."""
    return Decimal(amount).scaleb(-scale)


def int_to_scaled_int(amount: int, scale: int) -> int:
    """Convert an integer amount with scale to a ScaledAmount dict."""
    return decimal_to_scaled_int(Decimal(amount), scale)


def get_previous_billing_period(current_period: datetime) -> datetime:
    """Return the previous UTC billing period in YYYY-MM format."""
    if current_period.month == 1:
        return current_period.replace(year=current_period.year - 1, month=12)
    else:
        return current_period.replace(month=current_period.month - 1)
