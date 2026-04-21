from gantry.db.base import BaseSQLModel
from gantry.db.utils import (
    WithID,
    WithCreateTimestamp,
)
from gantry.management.project.models import Project
from gantry.service.utils.file_storage.models import File

from typing import Sequence
from pyexpat import model

from sqlalchemy import Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB


class RagBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Rag"}


class RagMetadata(WithCreateTimestamp, WithID, RagBaseSQLModel):
    """Metadata for RAG data."""

    __tablename__ = "Metadata"

    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(File.id, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)


class RagData(WithCreateTimestamp, WithID, RagBaseSQLModel):
    __tablename__ = "RagData"
    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(File.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )  # redundant but useful for querying without join

    text: Mapped[str | None] = mapped_column(Text, nullable=False)
    # placeholder for embedding column, actual type will be set dynamically
    embedding: Mapped[Sequence[float]] = mapped_column(VECTOR())
