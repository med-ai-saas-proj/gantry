"""Utilities for constructing SQLAlchemy models."""

from gantry.shared.utils.uuid_utils import uuid7

from uuid import UUID as PythonUUID
from datetime import datetime

from sqlalchemy import Uuid, DateTime, BigInteger, func, text
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
)


class WithID(MappedAsDataclass, kw_only=True):
    """Add id (int) and uuid (UUID) column to table."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        sort_order=-999,
        init=False,
        autoincrement=True,
    )


class WithUUID(MappedAsDataclass, kw_only=True):
    uuid: Mapped[PythonUUID] = mapped_column(
        Uuid,
        unique=True,
        index=True,
        nullable=False,
        default_factory=uuid7,
        # server_default=text("uuidv7()"),
        sort_order=-998,
        init=False,
    )


class WithClientUUID(MappedAsDataclass, kw_only=True):
    uuid: Mapped[PythonUUID] = mapped_column(
        Uuid,
        unique=True,
        index=True,
        nullable=False,
        sort_order=-997,
    )


class WithClientUUIDWithoutUnique(MappedAsDataclass, kw_only=True):
    uuid: Mapped[PythonUUID] = mapped_column(
        Uuid,
        index=True,
        nullable=False,
        sort_order=-997,
    )


class WithCreateUpdateTimestamp(MappedAsDataclass, kw_only=True):
    """Add created_at and updated_at to table."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
        init=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=func.now(),
        # server_onupdate=func.now(),
        nullable=False,
        init=False,
    )


class WithCreateTimestamp(MappedAsDataclass, kw_only=True):
    """Add created_at to table."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        # default=datetime.now(UTC).replace(tzinfo=None),
        server_default=func.now(),
        nullable=False,
        init=False,
    )
