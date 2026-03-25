"""DTOs for the billing module."""

from src.management.billing.models import BillingSourceProvider

from re import U
from uuid import UUID
from typing import TypedDict
from datetime import datetime

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


class BillingPing(TypedDict):
    """Input payload for requesting a billing HOLD."""

    organization_id: str
    project_id: int
    apikey_id: int
    amount: ScaledAmount  # maximum (worst-case) cost estimate
    details: dict  # e.g. {"llm_usages": {"gpt-4o": {"input_tokens": 100}}}


class HoldRequest(BaseModel):
    amount: ScaledAmount
    details: dict = {}


class ReleaseRequest(BaseModel):
    real_amount: ScaledAmount


class ManualPaymentResponse(BaseModel):
    hosted_invoice_url: str  # URL to hosted payment page on the payment gateway (e.g. Stripe Checkout) where the user can complete the payment


class TransactionInfo(BaseModel):
    transaction_id: UUID
    amount: ScaledAmount
    date: datetime
    project_id: int
    details: dict


class InvoiceInfo(BaseModel):
    invoice_id: str
    amount_due: ScaledAmount
    due_date: datetime


class StripeInvoiceInfo(BaseModel):
    invoice_id: str
    amount_due: ScaledAmount
    due_date: datetime
    hosted_invoice_url: str


type InvoiceDetailInfo = StripeInvoiceInfo  # can be extended to support multiple payment gateways with different invoice formats in the future


class SpendingLimitInfo(BaseModel):
    project_uid: UUID
    limit_amount: ScaledAmount
    current_spend: ScaledAmount


class UpdateSpendingLimitRequest(BaseModel):
    new_limit: ScaledAmount | None = (
        None  # if null, will remove spending limit and allow all charges to go through regardless of amount
    )
    project_uid: UUID | None = (
        None  # if null, will apply to whole organization instead of specific project
    )


class CreditInfo(BaseModel):
    credit_id: UUID
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
