"""API Key and permission entity."""

from __future__ import annotations

from src.db_v2.utils import (
    WithUUID,
    WithAutoIncrementBigIntPK,
    WithCreateUpdateTimestamp,
)

from .base import AuthBaseSQLModel
from .users import Users
from .permissions import Permissions

import datetime

from sqlalchemy import BIGINT, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column


API_KEY_TABLE_NAME = "ApiKeys"


class ApiKeyPermissions(
    AuthBaseSQLModel,
):
    """Association table between API Keys and Permissions."""

    __tablename__ = "ApiKeyPermissions"

    api_key_id: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey(f"{API_KEY_TABLE_NAME}.{WithAutoIncrementBigIntPK.ID_NAME}"),
        primary_key=True,
        index=True,
    )

    permission_name: Mapped[str] = mapped_column(
        String, ForeignKey(Permissions.name), primary_key=True, index=True
    )


class ApiKeys(
    WithCreateUpdateTimestamp,
    WithUUID,
    WithAutoIncrementBigIntPK,
    AuthBaseSQLModel,
):
    """API Key."""

    __tablename__ = API_KEY_TABLE_NAME

    owner_id: Mapped[int] = mapped_column(
        BIGINT, ForeignKey(Users.id), nullable=False
    )
    hashed_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expiration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=True
    )

    owner: Mapped[Users] = relationship(Users, init=False)

    permissions: Mapped[list[Permissions]] = relationship(
        Permissions, secondary=ApiKeyPermissions.__table__, init=False
    )
