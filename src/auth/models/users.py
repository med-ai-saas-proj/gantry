"""User entity."""

from src.db_v2.base import (
    BaseEntity,
)

import uuid
from uuid import uuid4

from sqlalchemy import UUID, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column


class User(BaseEntity):
    """User entity."""

    __tablename__ = "USERS"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, unique=True, nullable=False, default=uuid4
    )

    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
