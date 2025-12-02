"""User entity."""

from src.db_v2.utils import WithIDAndUUID, WithCreateUpdateTimestamp

from .base import AuthBaseSQLModel

import uuid
from uuid import uuid4

from sqlalchemy import UUID, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class Users(WithCreateUpdateTimestamp, WithIDAndUUID, AuthBaseSQLModel):
    """User entity."""

    __tablename__ = "USERS"

    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
