from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.service.billing.entities import BillingSourceType, BillingSourceStatus


class BillingChargeRequest(BaseModel):
    """Request to charge for an API call."""

    organization_id: UUID
    project_id: UUID
    amount_charged: Decimal = Field(ge=0, decimal_places=4)
    details: dict[str, Any] = Field(default_factory=dict)
    llm_usages: dict[str, Any] = Field(
        default_factory=dict,
        description="LLM usage details like {model_name: {tokens: 100, ...}}",
    )


class BillingChargeResponse(BaseModel):
    """Response after recording a billing charge."""

    transaction_id: UUID
    organization_id: UUID
    project_id: UUID
    amount_charged: Decimal
    billing_source_id: UUID | None
    timestamp: datetime


class ProjectBillingSummary(BaseModel):
    """Summary of billing for a project over a period."""

    project_id: UUID
    period_start: datetime
    period_end: datetime
    total_amount: Decimal
    transaction_count: int
    llm_usage_summary: dict[str, Any]


class MonthlyBillSummary(BaseModel):
    """Aggregated monthly bill summary."""

    bill_id: UUID
    organization_id: UUID
    project_id: UUID
    year: int
    month: int
    total_amount: Decimal
    transaction_count: int
    source_breakdown: dict[str, Any]
    llm_usage_summary: dict[str, Any]
    period_start: datetime
    period_end: datetime
    generated_at: datetime


class CreateBillingSourceRequest(BaseModel):
    """Request to create a new billing source."""

    organization_id: UUID
    project_id: UUID | None = None  # None = organization-level
    source_type: BillingSourceType
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    # For credits
    initial_credits: Decimal | None = Field(None, ge=0, decimal_places=4)

    # For 3rd party
    external_id: str | None = None
    external_metadata: dict[str, Any] = Field(default_factory=dict)

    priority: int = Field(default=0, ge=0)


class BillingSourceResponse(BaseModel):
    """Response with billing source details."""

    id: UUID
    organization_id: UUID
    project_id: UUID | None
    source_type: BillingSourceType
    status: BillingSourceStatus
    name: str
    description: str | None

    # For credits
    credit_balance: Decimal | None
    initial_credits: Decimal | None

    priority: int
    created_at: datetime
    updated_at: datetime


class UpdateBillingSourceRequest(BaseModel):
    """Request to update billing source."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    status: BillingSourceStatus | None = None
    priority: int | None = Field(None, ge=0)


class AddCreditsRequest(BaseModel):
    """Request to add credits to a billing source."""

    amount: Decimal = Field(gt=0, decimal_places=4)
