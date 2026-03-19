from datetime import datetime

from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from decimal import Decimal

from sqlalchemy import (
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
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

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
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

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

    month_start: Mapped[int] = mapped_column(Integer, nullable=True)  # month of start, e.g. 01
    year_start: Mapped[int] = mapped_column(Integer, nullable=True)  # year of start, e.g. 2024

    month_exp: Mapped[int] = mapped_column(Integer, nullable=True)  # month of expiration, e.g. 02
    year_exp: Mapped[int] = mapped_column(Integer, nullable=True)  # year of expiration, e.g. 2026

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

    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

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


class OrganizationSpendingLimit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    """Spending cap at the organization level. All amounts in USD.

    NULL on a limit field means no limit is set — falls back to global default.
    Project-level limits (ProjectSpendingLimit) take precedence over these.
    """

    __tablename__ = "OrganizationSpendingLimits"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )

    # NULL = no limit set (global default applies)
    monthly_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
    daily_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )


class ProjectSpendingLimit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    """Spending cap at the project level. All amounts in USD.

    Takes precedence over OrganizationSpendingLimit.
    NULL on a limit field means fall back to the org-level limit.
    """

    __tablename__ = "ProjectSpendingLimits"

    project_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True, index=True
    )

    # NULL = fall back to org-level limit
    monthly_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
    daily_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
