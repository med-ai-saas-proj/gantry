from src.db.base import BaseTimescaleSQLModel
from src.db.utils import WithID, WithClientUUIDv7, WithCreateUpdateTimestamp

import enum
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import (
    Date,
    Enum,
    Index,
    String,
    Numeric,
    DateTime,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


class BillingBaseSQLModel(BaseTimescaleSQLModel):
    """Base SQL Model for the billing module."""

    __abstract__ = True
    __table_args__ = {"schema": "Billing"}


class TimescaleDBDailyBillingSummary(BaseTimescaleSQLModel):
    """Daily aggregated billing data for efficient reporting.

    MUST NOT BE INSERTED/UPDATED/DELETED BY APPLICATION CODE.
    This is managed by a TimescaleDB continuous aggregate view.
    """

    __tablename__ = "daily_billing_summary"
    __table_args__ = {"schema": "Billing", "skip_autogenerate": True}

    bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    organization_id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    apikey_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    transaction_count: Mapped[int] = mapped_column(BigInteger)


class BillingTransaction(WithClientUUIDv7, BillingBaseSQLModel, WithID):
    """Individual charge record for each API call.

    All amounts are in USD. Currency conversion is handled by the payment
    provider layer, not here.

    Flow:
      1. Service calls HOLD(maximum_cost) before processing request.
      2. After processing, service calls RELEASE(uuid, real_cost).
      3. RELEASE deletes the hold and inserts this transaction record.
    """

    __tablename__ = "BillingTransactions"

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
        primary_key=True,
        init=False,
    )

    # apikey_id is enough, project_id and org_id can be derived from it
    apikey_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    # for quick access patterns, we also store project_id and org_id here (denormalization)
    project_id: Mapped[int] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    # Numeric avoids float rounding — critical for billing.
    # Postgres stores Numeric as varchar internally; (18, 8) is a soft limit,
    # hard limit is ~1000 digits. Fine for any realistic USD amount.
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )

    # e.g. { "llm_usages": { "gpt-4o": { "input_tokens": 100, "output_tokens": 50 } } }
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Credit(
    WithCreateUpdateTimestamp, WithID, WithClientUUIDv7, BillingBaseSQLModel
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


class BillingSourceState(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class BillingSourceProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    # Add more providers as needed (e.g. "braintree", "square", etc.)


class BillingSource(
    WithCreateUpdateTimestamp, WithID, WithClientUUIDv7, BillingBaseSQLModel
):
    __tablename__ = "BillingSources"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    source_type: Mapped[BillingSourceProvider] = mapped_column(
        Enum(BillingSourceProvider), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g. Stripe customer ID
    status: Mapped[BillingSourceState] = mapped_column(
        Enum(BillingSourceState),
        default=BillingSourceState.PENDING,
        server_default=BillingSourceState.PENDING,
    )


class BillingInvoice(
    WithCreateUpdateTimestamp, WithID, WithClientUUIDv7, BillingBaseSQLModel
):
    __tablename__ = "BillingInvoices"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    billing_period: Mapped[date] = mapped_column(
        Date, nullable=False, unique=True
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)

    used_credits: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), nullable=False, default=Decimal("0")
    )


class BillingInvoiceLineItem(
    WithCreateUpdateTimestamp, WithID, WithClientUUIDv7, BillingBaseSQLModel
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
        BigInteger, nullable=True, index=True
    )  # optional link to project


class SpendingLimitType(str, enum.Enum):
    MONTHLY = "monthly"
    DAILY = "daily"


class SpendingLimit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel, WithClientUUIDv7
):
    __tablename__ = "SpendingLimits"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, nullable=True, unique=True, index=True
    )

    limit_type: Mapped[SpendingLimitType] = mapped_column(
        Enum(SpendingLimitType, schema="Billing"), nullable=False
    )
    limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=8), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(organization_id, project_id, name="uq_spending_limit"),
        Index(
            "ix_spending_limits_org",
            organization_id,
            unique=True,
            postgresql_where=project_id.is_(None),  # global default record
        ),
    )
