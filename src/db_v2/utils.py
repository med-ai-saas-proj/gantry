"""Utilities for constructing SQLAlchemy models."""

from src.db_v2.base import naming_convention

from uuid import UUID as PythonUUID, uuid4
from datetime import datetime

from sqlalchemy import UUID, BIGINT, Column, DateTime, ForeignKey, func
from sqlalchemy.orm import (
    Mapped,
    DeclarativeBase,
    MappedAsDataclass,
    mapped_column,
)


class WithAutoIncrementBigIntPK(MappedAsDataclass, kw_only=True):
    """Add id (int) and uuid (UUID) column to table."""

    ID_NAME = "id"

    id: Mapped[int] = mapped_column(
        BIGINT, primary_key=True, autoincrement=True, init=False
    )


class WithUUID(MappedAsDataclass, kw_only=True):
    """Add uuid (UUID) column to table."""

    uid: Mapped[PythonUUID] = mapped_column(
        UUID,
        unique=True,
        nullable=False,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )


class WithAutoGenerateUUID(MappedAsDataclass, kw_only=True):
    """Add auto generate uuid (UUID) column to table."""

    uid: Mapped[PythonUUID] = mapped_column(
        UUID,
        unique=True,
        nullable=False,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
        init=False,
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
