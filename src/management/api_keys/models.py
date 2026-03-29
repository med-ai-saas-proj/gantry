from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithCreateUpdateTimestamp
from src.management.project.models import Project

from sqlalchemy import String, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY


class ApiKeyBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "ApiKey"}


class ApiKey(WithCreateUpdateTimestamp, WithID, ApiKeyBaseSQLModel):
    """Project-scoped API key with dynamic text permissions."""

    __tablename__ = "ApiKeys"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    hint: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_key: Mapped[str] = mapped_column(
        String(128), index=True, unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(String(4096), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(String(1024)),
        nullable=False,
        default=list,
        server_default="{}",
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id),
        nullable=False,
        index=True,
    )

    project: Mapped[Project] = relationship(Project)
