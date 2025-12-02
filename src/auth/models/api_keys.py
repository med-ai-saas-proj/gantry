"""API Key and permission entity."""

from __future__ import annotations

from src.db_v2.utils import (
    WithIDAndUUID,
    WithCreateUpdateTimestamp,
)

from .base import AuthBaseSQLModel
from .users import Users

import uuid
import datetime

from sqlalchemy import UUID, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column


class ApiKeys(WithCreateUpdateTimestamp, WithIDAndUUID, AuthBaseSQLModel):
    """API Key."""

    __tablename__ = "ApiKeys"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey(Users.id), nullable=False
    )
    hashed_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expiration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=True
    )


class Permissions(WithCreateUpdateTimestamp, WithIDAndUUID, AuthBaseSQLModel):
    """Permission class."""

    __tablename__ = "Permissions"

    name: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)


class ApiKeyPermissions(WithCreateUpdateTimestamp, AuthBaseSQLModel):
    """API Key and Permission relation entity."""

    __tablename__ = "ApiKeyPermissions"

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey(ApiKeys.id), primary_key=True
    )
    permission_name: Mapped[str] = mapped_column(
        String, ForeignKey(Permissions.name), primary_key=True
    )
