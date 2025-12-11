"""API Key and permission entity."""

from __future__ import annotations

from src.db.utils import (
    WithID,
    WithUUID,
    WithCreateUpdateTimestamp,
)

from .base import AuthBaseSQLModel
from .users import Users

import datetime

from sqlalchemy import Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column


class ApiKeys(WithCreateUpdateTimestamp, WithID, AuthBaseSQLModel):
    """API Key."""

    __tablename__ = "ApiKeys"

    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Users.id), nullable=False
    )
    hashed_key: Mapped[str] = mapped_column(
        Text, index=True, unique=True, nullable=False
    )
    expiration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=True
    )


class Permissions(WithCreateUpdateTimestamp, WithID, AuthBaseSQLModel):
    """Permission class."""

    __tablename__ = "Permissions"

    name: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)


class ApiKeyPermissions(AuthBaseSQLModel):
    """API Key and Permission relation entity."""

    __tablename__ = "ApiKeyPermissions"

    api_key_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(ApiKeys.id), primary_key=True
    )
    permission_id: Mapped[BigInteger] = mapped_column(
        BigInteger, ForeignKey(Permissions.id), primary_key=True
    )
