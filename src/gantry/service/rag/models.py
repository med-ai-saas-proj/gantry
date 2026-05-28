from gantry.db.base import BaseSQLModel
from gantry.db.utils import (
    WithID,
    WithCreateTimestamp,
)
from gantry.management.project.models import Project
from gantry.service.file_storage.models import File

from typing import Sequence

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
    file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(File.id, ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )  # redundant but useful for querying without join
    lang: Mapped[str | None] = mapped_column(Text, nullable=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # placeholder for embedding column, actual type will be set dynamically
    embedding: Mapped[Sequence[float]] = mapped_column(VECTOR())
