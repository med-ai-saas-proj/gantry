from src.db.base import BaseTimescaleSQLModel
from src.db.utils import (
    WithID,
    WithUUID,
    WithCreateUpdateTimestamp,
    WithClientUUIDWithoutUnique,
)

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


AMOUNT_PRECISION = 18
AMOUNT_SCALE = 8
AMOUNT_COLUMN_TYPE = Numeric(precision=AMOUNT_PRECISION, scale=AMOUNT_SCALE)


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

    total_amount: Mapped[Decimal] = mapped_column(Numeric())
    transaction_count: Mapped[int] = mapped_column(BigInteger)


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CAPTURED = "CAPTURED"
    EXPIRED = "EXPIRED"


# timescaledb hypertable doesnot allow having others unique index except primary key
class BillingTransaction(
    WithClientUUIDWithoutUnique, BillingBaseSQLModel, WithID
):
    __tablename__ = "BillingTransactions"

    # use server time instead of db time to avoid billing period not matching
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
        primary_key=True,
        # init=False,
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

    amount: Mapped[Decimal] = mapped_column(AMOUNT_COLUMN_TYPE, nullable=False)
    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, schema="Billing"),
        nullable=False,
        index=True,
        default=TransactionStatus.PENDING,
    )

    # e.g. { "llm_usages": { "gpt-4o": { "input_tokens": 100, "output_tokens": 50 } } }
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Credit(WithCreateUpdateTimestamp, BillingBaseSQLModel):
    __tablename__ = "Credits"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, primary_key=True
    )
    amount: Mapped[Decimal] = mapped_column(AMOUNT_COLUMN_TYPE, nullable=False)


class CreditTransaction(WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel):
    __tablename__ = "CreditTransactions"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(AMOUNT_COLUMN_TYPE, nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False)


class BillingSourceProvider(str, enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    # Add more providers as needed (e.g. "braintree", "square", etc.)


# NOTE: THIS IMMUTABLE ONCE CREATED. DO NOT UPDATE/DELETE
class BillingSource(
    WithCreateUpdateTimestamp, WithID, WithUUID, BillingBaseSQLModel
):
    __tablename__ = "BillingSources"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, unique=True
    )
    source_type: Mapped[BillingSourceProvider] = mapped_column(
        Enum(BillingSourceProvider), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g. Stripe customer ID


class BillingInvoice(
    WithCreateUpdateTimestamp, WithID, WithUUID, BillingBaseSQLModel
):
    __tablename__ = "BillingInvoices"

    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    billing_period: Mapped[date] = mapped_column(Date, nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        AMOUNT_COLUMN_TYPE, nullable=False
    )
    provider_invoice_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )  # e.g. Stripe invoice ID
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)

    used_credits: Mapped[Decimal] = mapped_column(
        AMOUNT_COLUMN_TYPE, nullable=False, default=Decimal("0")
    )

    __table_args__ = (
        UniqueConstraint(
            organization_id, billing_period, name="uq_org_billing_period"
        ),
        BillingBaseSQLModel.__table_args__,
    )


class BillingInvoiceLineItem(
    WithCreateUpdateTimestamp, WithID, WithUUID, BillingBaseSQLModel
):
    __tablename__ = "BillingInvoiceLineItems"

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(BillingInvoice.id, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )  # foreign key to BillingInvoice.id
    description: Mapped[str] = mapped_column(String(256), nullable=False)

    amount: Mapped[Decimal] = mapped_column(AMOUNT_COLUMN_TYPE, nullable=False)
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )  # optional link to project


class SpendingLimitType(str, enum.Enum):
    MONTHLY = "monthly"
    # DAILY = "daily"


class SpendingLimit(
    WithCreateUpdateTimestamp, WithID, BillingBaseSQLModel, WithUUID
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
        AMOUNT_COLUMN_TYPE, nullable=True
    )

    __table_args__ = (
        UniqueConstraint(organization_id, project_id, name="uq_spending_limit"),
        Index(
            "ix_spending_limits_org",
            organization_id,
            unique=True,
            postgresql_where=project_id.is_(None),  # global default record
        ),
        BillingBaseSQLModel.__table_args__,
    )
