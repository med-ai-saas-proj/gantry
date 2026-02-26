from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, DECIMAL, Index, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class BillingSourceType(str, Enum):
    """Types of billing sources."""

    CREDITS = "credits"
    # For future 3rd party payment integrations
    STRIPE = "stripe"
    PAYPAL = "paypal"


class BillingSourceStatus(str, Enum):
    """Status of billing sources."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPLETED = "depleted"


class BillingSource(BaseModel):
    """
    Represents a billing source (payment method) for an organization/project.
    Can be credits, or future 3rd party payment integrations.
    """

    __tablename__ = "billing_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        nullable=True, index=True
    )  # None = org-level

    source_type: Mapped[BillingSourceType] = mapped_column(String(50), nullable=False)
    status: Mapped[BillingSourceStatus] = mapped_column(
        String(50), nullable=False, default=BillingSourceStatus.ACTIVE
    )

    # For credits
    credit_balance: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 4), nullable=True
    )
    initial_credits: Mapped[Decimal | None] = mapped_column(
        DECIMAL(12, 4), nullable=True
    )

    # For 3rd party integrations
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # Priority for selecting billing source (higher = preferred)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now, nullable=False
    )

    __table_args__ = (
        Index("ix_billing_sources_org_project", "organization_id", "project_id"),
        Index("ix_billing_sources_status_priority", "status", "priority"),
    )


class BillingTransaction(BaseModel):
    """
    Represents a single billing transaction for API usage.
    Each API call creates one transaction record.
    """

    __tablename__ = "billing_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    billing_source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("billing_sources.id"), nullable=True
    )

    amount_charged: Mapped[Decimal] = mapped_column(DECIMAL(10, 4), nullable=False)

    # Additional details about the transaction
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # LLM usage details (model name, tokens, etc.)
    llm_usages: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # When the transaction occurred (UTC)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # For audit trail
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)

    __table_args__ = (
        Index("ix_billing_transactions_project_timestamp", "project_id", "timestamp"),
        Index("ix_billing_transactions_org_timestamp", "organization_id", "timestamp"),
        Index("ix_billing_transactions_source", "billing_source_id"),
    )


class MonthlyBill(BaseModel):
    """
    Aggregated monthly billing summary for a project.
    Generated at the end of each calendar month.
    """

    __tablename__ = "monthly_bills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int] = mapped_column(nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 4), nullable=False)
    transaction_count: Mapped[int] = mapped_column(nullable=False)

    source_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    llm_usage_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)

    # When this bill was generated
    generated_at: Mapped[datetime] = mapped_column(nullable=False)

    # For audit trail
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, nullable=False)

    __table_args__ = (
        # Unique constraint to prevent duplicate bills
        Index(
            "ix_monthly_bills_unique",
            "organization_id",
            "project_id",
            "year",
            "month",
            unique=True,
        ),
        Index("ix_monthly_bills_org_date", "organization_id", "year", "month"),
    )
