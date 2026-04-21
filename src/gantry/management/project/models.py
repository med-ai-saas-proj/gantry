"""SQLAlchemy models for the Project module."""

from gantry.db.base import BaseSQLModel
from gantry.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    BigInteger,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB


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


class ProjectMember(WithCreateUpdateTimestamp, ProjectBaseSQLModel):
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


class ProjectSettings(WithCreateUpdateTimestamp, ProjectBaseSQLModel):
    """Per-project settings stored in Postgres."""

    __tablename__ = "Settings"

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        primary_key=True,
    )
    rate_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        doc="Requests per minute. NULL inherits organization/default limit.",
    )
    spending_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
        doc="Monthly spending limit as a scaled integer. NULL means unlimited.",
    )
    extra: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Additional flat key-value settings.",
    )
