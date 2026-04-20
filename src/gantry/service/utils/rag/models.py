from gantry.db.base import BaseSQLModel
from gantry.db.utils import (
    WithID,
    WithCreateTimestamp,
)
from gantry.management.project.models import Project
from gantry.service.utils.file_storage.models import File

from typing import Sequence

from sqlalchemy import Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.sql.schema import ForeignKey


class RagBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "Rag"}


class RagData(WithCreateTimestamp, WithID, RagBaseSQLModel):
    __abstract__ = True

    file_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(File.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=False)
    # placeholder for embedding column, actual type will be set dynamically
    embedding: Mapped[Sequence[float]] = mapped_column(VECTOR())
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )  # redundant but useful for querying without join
