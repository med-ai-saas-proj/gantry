from typing import TypedDict
from decimal import Decimal


class ScaledAmount(TypedDict):
    """Fixed-point monetary amount — avoids float/Decimal in API inputs.

    actual_value = value / 10^scale
    Example: 3.14159 USD → {"value": 314159, "scale": 5}

    Reference: https://stackoverflow.com/a/77703260/31748896
    """

    value: int
    scale: int


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
