"""Base entity for SQLAlchemy models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import Mapped, mapped_column, declarative_base


metadata = MetaData(schema="app")
Base = declarative_base(metadata=metadata)


class BaseEntity(Base):
    """Base Entity."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=datetime.now(UTC).replace(tzinfo=None),
        server_onupdate=func.now(),
        nullable=False,
    )
