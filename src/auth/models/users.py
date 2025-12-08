"""User entity."""

from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from .base import AuthBaseSQLModel

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class Users(WithCreateUpdateTimestamp, WithID, WithUUID, AuthBaseSQLModel):
    """User entity."""

    __tablename__ = "Users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
