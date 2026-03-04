from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithCreateUpdateTimestamp

import enum
from decimal import Decimal

from sqlalchemy import (
    Enum,
    Index,
    String,
    Numeric,
    BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class BillingBaseSQLModel(BaseSQLModel):
    """Base SQL Model for the billing module."""

    __abstract__ = True
    __table_args__ = {"schema": "Billing"}


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    committed = "committed"
    reversed = "reversed"


class AggregateStatus(str, enum.Enum):
    open = "open"
    finalized = "finalized"


class SpendingLimitPeriod(str, enum.Enum):
    daily = "daily"
    monthly = "monthly"


class BillingTransaction(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel
):
    """Individual charge record for each API call.

    All amounts are in USD. Currency conversion is handled by the payment
    provider layer, not here.
    """

    __tablename__ = "BillingTransactions"
    __table_args__ = (
        Index(
            "ix_billing_transactions_project_created",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_billing_transactions_org_created",
            "organization_id",
            "created_at",
        ),
        {"schema": "Billing"},
    )

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    apikey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Numeric avoids float rounding — critical for billing.
    # Postgres stores Numeric as varchar internally; (18, 8) is a soft limit,
    # hard limit is ~1000 digits. Fine for any realistic USD amount.
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, schema="Billing"),
        nullable=False,
        default=TransactionStatus.committed,
    )

    # e.g. { "llm_usages": { "gpt-4o": { "input_tokens": 100, "output_tokens": 50 } } }
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class MonthlyAggregate(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    """Pre-aggregated billing total per project per calendar month.

    All amounts are in USD.

    Period format:
      - `billing_period`  — "2026-02"  (monthly granularity, used as primary key)

    Caching strategy (implemented later in BILL-008):
      - Current month's aggregate is cached in Redis under
        key `billing:agg:{project_id}:{billing_period}` for hot reads/writes.
      - Postgres is always the source of truth.
      - Finalized (past) months are read directly from Postgres — they never change.
    """

    __tablename__ = "MonthlyAggregates"
    __table_args__ = (
        Index(
            "ix_monthly_aggregates_project_period",
            "project_id",
            "billing_period",
            unique=True,
        ),
        {"schema": "Billing"},
    )

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    # "2026-02" — always calendar month, always UTC
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )
    status: Mapped[AggregateStatus] = mapped_column(
        Enum(AggregateStatus, schema="Billing"),
        nullable=False,
        default=AggregateStatus.open,
    )


class SpendingLimit(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    """Spending cap per project or per organization. All amounts in USD.

    If `project_id` is NULL, the limit applies at the org level.
    Project-level limit takes precedence over org-level limit.
    """

    __tablename__ = "SpendingLimits"
    __table_args__ = (
        Index(
            "ix_spending_limits_project",
            "project_id",
            unique=True,
        ),
        Index(
            "ix_spending_limits_org",
            "organization_id",
            unique=True,
        ),
        {"schema": "Billing"},
    )

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    # nullable — if null, limit applies at the org level
    project_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    limit_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    period: Mapped[SpendingLimitPeriod] = mapped_column(
        Enum(SpendingLimitPeriod, schema="Billing"),
        nullable=False,
        default=SpendingLimitPeriod.monthly,
    )
