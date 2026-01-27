from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column


class ProjectBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Project"}


class Project(ProjectBaseSQLModel, WithUUID, WithID, WithCreateUpdateTimestamp):
    """Project model."""

    __tablename__ = "Projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False)
