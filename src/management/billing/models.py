from datetime import date, datetime

from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Numeric,
    BigInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from src.management.projects.models import Project


class BillingBaseSQLModel(BaseSQLModel):
    """Base SQL Model for the billing module."""

    __abstract__ = True
    __table_args__ = {"schema": "Billing"}


class BillingTransaction(
    WithCreateUpdateTimestamp, WithUUID, BillingBaseSQLModel, WithID
):
    """Individual charge record for each API call.

    All amounts are in USD. Currency conversion is handled by the payment
    provider layer, not here.

    Flow:
      1. Service calls HOLD(maximum_cost) before processing request.
      2. After processing, service calls RELEASE(uuid, real_cost).
      3. RELEASE deletes the hold and inserts this transaction record.
    """

    __tablename__ = "BillingTransactions"

    # apikey_id is enough, project_id and org_id can be derived from it
    apikey_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )

    # Numeric avoids float rounding — critical for billing.
    # Postgres stores Numeric as varchar internally; (18, 8) is a soft limit,
    # hard limit is ~1000 digits. Fine for any realistic USD amount.
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )

    # e.g. { "llm_usages": { "gpt-4o": { "input_tokens": 100, "output_tokens": 50 } } }
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class ProjectMonthlyAggregate(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    """Pre-aggregated billing total per project per calendar month.

    All amounts are in USD.

    Period format: "2026-02" — calendar month, UTC boundary.

    Caching strategy (TODO: implement in BILL-008):
      - Current month's aggregate is cached in Redis under
        key `billing:agg:{project_id}:{billing_period}` for hot reads/writes.
      - Postgres is always the source of truth.
      - Finalized (past) months are read directly from Postgres — they never change.
    """

    __tablename__ = "ProjectMonthlyAggregates"
    __table_args__ = (
        Index(
            "ix_project_monthly_aggregates_project_period",
            "project_id",
            "billing_period",
            unique=True,
        ),
        {"schema": "Billing"},
    )

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # "2026-02" — always calendar month, always UTC
    billing_period: Mapped[date] = mapped_column(Date, nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )
    # False = open, True = finalized
    is_finalized: Mapped[bool] = mapped_column(nullable=False, default=False)

class OrganizationMonthlyAggregate(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    """Pre-aggregated billing total per organization per calendar month.

    All amounts are in USD.

    Period format: "2026-02" — calendar month, UTC boundary.
    """

    __tablename__ = "OrganizationMonthlyAggregates"
    __table_args__ = (
        Index(
            "ix_organization_monthly_aggregates_organization_period",
            "organization_id",
            "billing_period",
            unique=True,
        ),
        {"schema": "Billing"},
    )

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )

    # "2026-02" — always calendar month, always UTC
    billing_period: Mapped[date] = mapped_column(Date, nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )
    # False = open, True = finalized
    is_finalized: Mapped[bool] = mapped_column(nullable=False, default=False)


class Credit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    __tablename__ = "Credits"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(String(512), nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expired_date: Mapped[date] = mapped_column(Date, nullable=False)

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    current_spent: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )

class BillingSource(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    __tablename__ = "BillingSources"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "stripe", "paypal"
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. Stripe customer ID

    __table_args__ = (
        UniqueConstraint(organization_id, source_type, name="uq_billing_source"),
     )


class BillingInvoice(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    __tablename__ = "BillingInvoices"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    billing_period: Mapped[date] = mapped_column(Date, nullable=False, unique=True)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)

    used_credits: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )


class BillingInvoiceLineItem(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    __tablename__ = "BillingInvoiceLineItems"

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(BillingInvoice.id, ondelete="CASCADE"), 
        nullable=False, 
        index=True,
    )

    description: Mapped[str] = mapped_column(String(256), nullable=False)

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        ForeignKey(Project.id, ondelete="SET NULL"),
        nullable=True, index=True
    ) # optional link to project


class SpendingLimit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    __tablename__ = "SpendingLimits"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey(Project.id, ondelete="CASCADE"),
        nullable=True, unique=True, index=True
    )

    monthly_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
    daily_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(organization_id, project_id, name="uq_spending_limit"),
        Index(
            "ix_spending_limits_org",
            organization_id,
            unique=True,
            postgresql_where=project_id.is_(None)  # global default record
        ),
     )