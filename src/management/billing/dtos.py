"""DTOs for the billing module."""

from typing import TypedDict


class ScaledAmount(TypedDict):
    """Fixed-point monetary amount — avoids float/Decimal in API inputs.

    actual_value = value / 10^scale
    Example: 3.14159 USD → {"value": 314159, "scale": 5}

    Reference: https://stackoverflow.com/a/77703260/31748896
    """

    value: int
    scale: int


class BillingPing(TypedDict):
    """Input payload for requesting a billing HOLD."""

    organization_id: str
    project_id: int
    apikey_id: int
    amount: ScaledAmount  # maximum (worst-case) cost estimate
    details: dict  # e.g. {"llm_usages": {"gpt-4o": {"input_tokens": 100}}}
