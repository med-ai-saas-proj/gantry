"""Permissions model."""

from src.auth.models import AuthBaseSQLModel
from src.db_v2.utils import WithCreateUpdateTimestamp

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Permissions(WithCreateUpdateTimestamp, AuthBaseSQLModel):
    """Permission class."""

    __tablename__ = "Permissions"

    name: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=True)
