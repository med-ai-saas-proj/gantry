from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    llm_usage_summary: dict[str, Any]
    period_start: datetime
    period_end: datetime
    generated_at: datetime
