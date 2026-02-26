from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DECIMAL, Index
from sqlalchemy.orm import Mapped, mapped_column

from pydantic import BaseModel


class BillingTransaction(BaseModel):
    """
    Represents a single billing transaction for API usage.
    Each API call creates one transaction record.
    """

    __tablename__ = "billing_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

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
        # Composite index for efficient querying by project and time
        Index("ix_billing_transactions_project_timestamp", "project_id", "timestamp"),
        # Composite index for organization-level queries
        Index("ix_billing_transactions_org_timestamp", "organization_id", "timestamp"),
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
        # Index for listing bills
        Index("ix_monthly_bills_org_date", "organization_id", "year", "month"),
    )
