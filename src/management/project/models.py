"""SQLAlchemy models for the Project module."""

from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    BigInteger,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


class ProjectBaseSQLModel(BaseSQLModel):
    """Base SQL model for the Project schema."""

    __abstract__ = True
    __table_args__ = {"schema": "Project"}


class Project(WithCreateUpdateTimestamp, WithUUID, WithID, ProjectBaseSQLModel):
    """Project metadata."""

    __tablename__ = "Projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(1024), nullable=True, default=None
    )
    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class ProjectMembership(WithCreateUpdateTimestamp, ProjectBaseSQLModel):
    """User membership inside a project."""

    __tablename__ = "ProjectMembers"

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        init=False,
    )
