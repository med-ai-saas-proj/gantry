"""DTOs for the billing module."""

from src.management.billing.models import (
    BillingSourceProvider,
)

from uuid import UUID
from typing import Sequence, TypedDict
from decimal import Decimal
from datetime import date, datetime

from pydantic import BaseModel
from typing_extensions import Literal


class ScaledAmount(TypedDict):
    """Fixed-point monetary amount — avoids float/Decimal in API inputs.

    actual_value = value / 10^scale
    Example: 3.14159 USD → {"value": 314159, "scale": 5}

    Reference: https://stackoverflow.com/a/77703260/31748896
    """

    value: int
    scale: int


class PostRequest(BaseModel):
    amount: ScaledAmount
    details: dict = {}
    capture: bool = False


class CaptureRequest(BaseModel):
    real_amount: ScaledAmount


class ManualPaymentResponse(BaseModel):
    hosted_invoice_url: str  # URL to hosted payment page on the payment gateway (e.g. Stripe Checkout) where the user can complete the payment


class BillingSourceResponse(BaseModel):
    billing_source_uid: UUID
    organization_id: str
    source_type: BillingSourceProvider
    created_at: datetime


class BillingAddressResponse(BaseModel):
    line1: str | None
    line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None


class BillingSourceDetailResponse(BillingSourceResponse):
    provider_id: str
    email: str | None
    phone: str | None
    name: str | None
    billing_address: BillingAddressResponse | None


class TransactionInfoResponse(BaseModel):
    transaction_uid: UUID
    amount: Decimal
    date: datetime
    project_uid: UUID
    details: dict
    captured_at: datetime | None


class InvoiceInfoResponse(BaseModel):
    invoice_uid: UUID
    billing_period: date
    total_amount: Decimal
    paid_at: datetime | None
    details: dict
    used_credits: Decimal


class InvoiceItemInfoResponse(BaseModel):
    description: str
    amount: Decimal
    project_uid: UUID | None
    project_name: str | None


class InvoiceDetailInfoResponse(InvoiceInfoResponse):
    line_items: Sequence[
        InvoiceItemInfoResponse
    ]  # each dict contains description, amount, and project_id of the line item


class SpendingLimitInfoResponse(BaseModel):
    project_uid: str | None
    limit_amount: ScaledAmount
    current_spend: ScaledAmount


class UpdateSpendingLimitRequest(BaseModel):
    new_limit: ScaledAmount | None = (
        None  # if null, will remove spending limit and allow all charges to go through regardless of amount
    )


class CreditInfoResponse(BaseModel):
    credit_uid: str
    amount: ScaledAmount
    name: str
    current_spent: ScaledAmount
    start_month: int
    start_year: int
    exp_month: int
    exp_year: int
    note: str | None = None


class AddCreditRequest(BaseModel):
    amount: ScaledAmount
    organization_id: str
    name: str
    note: str | None = None
    amount: ScaledAmount
    start_month: int
    start_year: int
    exp_month: int
    exp_year: int


class BillingAddress(BaseModel):
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str
    country: str


class AddBillingSourceRequest(BaseModel):
    name: str
    email: str
    phone: str
    address: BillingAddress
    provider: Literal[BillingSourceProvider.STRIPE]


class UpdateBillingSourceRequest(BaseModel):
    new_address: BillingAddress | None
    new_email: str | None
    new_phone: str | None
