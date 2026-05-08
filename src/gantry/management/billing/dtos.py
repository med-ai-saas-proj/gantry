"""DTOs for the billing module."""

from gantry.shared.utils.scaled_amount import ScaledAmount

from .models import (
    TransactionStatus,
    BillingSourceProvider,
)

from uuid import UUID
from typing import Literal, Sequence, TypedDict
from decimal import Decimal
from datetime import date, datetime

from pydantic import BaseModel


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
    project_uuid: UUID
    details: dict
    captured_at: datetime | None
    status: TransactionStatus


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
    project_uuid: UUID | None
    project_name: str | None


class InvoiceDetailInfoResponse(InvoiceInfoResponse):
    line_items: Sequence[
        InvoiceItemInfoResponse
    ]  # each dict contains description, amount, and project_id of the line item


class SpendingLimitInfoResponse(BaseModel):
    project_uuid: str | None
    limit_amount: ScaledAmount
    current_spend: ScaledAmount


class UpdateSpendingLimitRequest(BaseModel):
    new_limit: ScaledAmount | None = (
        None  # if null, will remove spending limit and allow all charges to go through regardless of amount
    )


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


class CreditInfoResponse(BaseModel):
    amount: Decimal


class AddCreditRequest(BaseModel):
    org_id: str
    amount: ScaledAmount
    description: str | None = None


class CreditTransactionInfoResponse(BaseModel):
    amount: Decimal
    description: str
    created_at: datetime
