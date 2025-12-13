from src.db.base import BaseSQLModel
from src.db.utils import (
    WithID,
    WithCreateUpdateTimestamp,
)

from sqlalchemy import Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column


class ApiKeyBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "ApiKey"}


class Permission(WithCreateUpdateTimestamp, WithID, ApiKeyBaseSQLModel):
    """Permission class."""

    __tablename__ = "Permissions"

    name: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)


class ApiKey(WithCreateUpdateTimestamp, WithID, ApiKeyBaseSQLModel):
    """API Key."""

    __tablename__ = "ApiKeys"

    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    hashed_key: Mapped[str] = mapped_column(
        Text, index=True, unique=True, nullable=False
    )
    # expiration_date: Mapped[datetime.datetime] = mapped_column(
    #     DateTime, nullable=True
    # )
    permissions: Mapped[list[Permission]] = relationship(
        Permission, secondary=lambda: ApiKeyPermission.__table__
    )


class ApiKeyPermission(ApiKeyBaseSQLModel):
    """API Key and Permission relation entity."""

    __tablename__ = "ApiKeyPermissions"

    apikey_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(ApiKey.id), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Permission.id), primary_key=True
    )
