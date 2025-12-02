"""Utilities for constructing SQLAlchemy models."""

from uuid import UUID as PythonUUID, uuid4
from datetime import datetime

from sqlalchemy import Uuid, Integer, DateTime, func
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
)


class WithIDAndUUID(MappedAsDataclass, kw_only=True):
    """Add id (int) and uuid (UUID) column to table."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[PythonUUID] = mapped_column(
        Uuid,
        unique=True,
        index=True,
        nullable=False,
        default_factory=uuid4,
    )


class WithCreateUpdateTimestamp(MappedAsDataclass, kw_only=True):
    """Add created_at and updated_at to table."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=func.now(),
        # server_onupdate=func.now(),
        nullable=False,
    )
