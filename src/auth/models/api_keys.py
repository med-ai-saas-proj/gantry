"""API Key and permission entity."""

from src.db_v2.base import (
    BaseEntity,
)
from src.auth.models.users import User

import uuid
import datetime

from sqlalchemy import (
    UUID,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column


class ApiKeyPermissions(BaseEntity):
    """API Key and Permission relation entity."""

    __tablename__ = "API_KEY_PERMISSIONS"

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("api_keys.id"), primary_key=True
    )
    permission_name: Mapped[str] = mapped_column(
        String, ForeignKey("permissions.name"), primary_key=True
    )


class ApiKey(BaseEntity):
    """API Key."""

    __tablename__ = "API_KEYS"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, unique=True, nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id"), nullable=False
    )
    hashed_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expiration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=True
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=ApiKeyPermissions.__table__,
        back_populates="api_keys",
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[owner_id])


class Permission(BaseEntity):
    """Permission class."""

    __tablename__ = "PERMISSIONS"

    name: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)

    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey",
        secondary=ApiKeyPermissions.__table__,
        back_populates="permissions",
    )
