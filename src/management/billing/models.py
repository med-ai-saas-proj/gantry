from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithCreateTimestamp, WithCreateUpdateTimestamp

from decimal import Decimal

from sqlalchemy import (
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


class BillingTransaction(WithCreateTimestamp, WithID, BillingBaseSQLModel):
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


class BillingHold(WithCreateTimestamp, WithID, BillingBaseSQLModel):
    """Temporary hold on funds before the real cost is known.

    Created by HOLD(maximum_cost), deleted by RELEASE(uuid, real_cost).
    Used to check spending limits before processing a request.
    """

    __tablename__ = "BillingHolds"

    apikey_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )


class MonthlyAggregate(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    """Pre-aggregated billing total per project per calendar month.

    All amounts are in USD.

    Period format: "2026-02" — calendar month, UTC boundary.

    Caching strategy (TODO: implement in BILL-008):
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

    project_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # "2026-02" — always calendar month, always UTC
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )
    # False = open, True = finalized
    is_finalized: Mapped[bool] = mapped_column(nullable=False, default=False)


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

    project_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )

    # NULL = fall back to org-level limit
    monthly_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
    daily_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )
