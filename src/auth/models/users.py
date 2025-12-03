"""User entity."""

from src.db_v2.utils import (
    WithAutoGenerateUUID,
    WithAutoIncrementBigIntPK,
    WithCreateUpdateTimestamp,
)

from .base import AuthBaseSQLModel

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class Users(
    WithCreateUpdateTimestamp,
    WithAutoGenerateUUID,
    WithAutoIncrementBigIntPK,
    AuthBaseSQLModel,
):
    """User entity."""

    __tablename__ = "Users"

    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
